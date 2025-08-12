from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count, Sum, Avg, F
from django.utils import timezone
from datetime import datetime, timedelta
import stripe
from decimal import Decimal
from .models import *
from .serializers import *


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 100

class LunchBoxViewSet(viewsets.ModelViewSet):
    """API pour les boîtes à lunch"""
    queryset = LunchBox.objects.filter(is_available=True)
    serializer_class = LunchBoxSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtres
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category__slug=category)
        
        # Filtres diététiques
        if self.request.query_params.get('vegetarian'):
            queryset = queryset.filter(is_vegetarian=True)
        if self.request.query_params.get('vegan'):
            queryset = queryset.filter(is_vegan=True)
        if self.request.query_params.get('gluten_free'):
            queryset = queryset.filter(is_gluten_free=True)
        
        # Recherche
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search) |
                Q(ingredients__icontains=search)
            )
        
        # Tri
        sort = self.request.query_params.get('sort', '-created_at')
        if sort == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort == 'popular':
            queryset = queryset.order_by('-sales_count')
        elif sort == 'rating':
            queryset = queryset.annotate(
                avg_rating=Avg('reviews__rating')
            ).order_by('-avg_rating')
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """Obtenir les avis d'un produit"""
        lunch_box = self.get_object()
        reviews = Review.objects.filter(
            lunch_box=lunch_box,
            is_approved=True
        ).select_related('user')
        
        data = [{
            'id': review.id,
            'user': review.user.get_full_name() or review.user.username,
            'rating': review.rating,
            'comment': review.comment,
            'created_at': review.created_at
        } for review in reviews]
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def bestsellers(self, request):
        """Top 10 des meilleures ventes"""
        bestsellers = self.queryset.order_by('-sales_count')[:10]
        serializer = self.get_serializer(bestsellers, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        """Recommandations personnalisées"""
        if request.user.is_authenticated:
            # Basé sur les commandes précédentes
            user_categories = OrderItem.objects.filter(
                order__user=request.user
            ).values_list('lunch_box__category', flat=True).distinct()
            
            recommendations = self.queryset.filter(
                category__in=user_categories
            ).exclude(
                id__in=OrderItem.objects.filter(
                    order__user=request.user
                ).values_list('lunch_box_id', flat=True)
            ).order_by('-sales_count')[:6]
        else:
            # Produits populaires pour les visiteurs
            recommendations = self.queryset.order_by('-sales_count')[:6]
        
        serializer = self.get_serializer(recommendations, many=True)
        return Response(serializer.data)

class CartViewSet(viewsets.ViewSet):
    """API pour le panier"""
    permission_classes = [AllowAny]
    
    def get_cart(self, request):
        if request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=request.user)
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.save()
                session_key = request.session.session_key
            cart, created = Cart.objects.get_or_create(session_key=session_key)
        return cart
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Obtenir le panier actuel"""
        cart = self.get_cart(request)
        items = []
        
        for item in cart.items.select_related('lunch_box'):
            items.append({
                'id': item.id,
                'lunch_box': {
                    'id': item.lunch_box.id,
                    'name': item.lunch_box.name,
                    'price': str(item.lunch_box.price),
                    'image': item.lunch_box.image.url if item.lunch_box.image else None
                },
                'quantity': item.quantity,
                'customization_notes': item.customization_notes,
                'total': str(item.get_total())
            })
        
        # Récupérer les codes promo de la session
        promo_codes = []
        if 'promo_codes' in request.session:
            promo_codes = PromoCode.objects.filter(
                code__in=request.session['promo_codes'],
                is_active=True
            )
        
        totals = calculate_cart_totals(cart, promo_codes)
        
        return Response({
            'items': items,
            'item_count': cart.items.count(),
            'subtotal': str(totals['subtotal']),
            'discount': str(totals['discount']),
            'tax': str(totals['tax']),
            'delivery_fee': str(totals['delivery_fee']),
            'total': str(totals['total']),
            'promo_codes': [code.code for code in promo_codes]
        })
    
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Ajouter un article au panier"""
        cart = self.get_cart(request)
        lunch_box_id = request.data.get('lunch_box_id')
        quantity = int(request.data.get('quantity', 1))
        customization = request.data.get('customization_notes', '')
        
        try:
            lunch_box = LunchBox.objects.get(id=lunch_box_id, is_available=True)
        except LunchBox.DoesNotExist:
            return Response(
                {'error': 'Produit non disponible'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            lunch_box=lunch_box,
            defaults={'quantity': quantity, 'customization_notes': customization}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        return Response({
            'success': True,
            'message': f'{lunch_box.name} ajouté au panier',
            'cart_count': cart.items.count()
        })
    
    @action(detail=False, methods=['patch'])
    def update_item(self, request):
        """Mettre à jour la quantité d'un article"""
        item_id = request.data.get('item_id')
        quantity = int(request.data.get('quantity', 1))
        
        try:
            cart = self.get_cart(request)
            item = cart.items.get(id=item_id)
            
            if quantity <= 0:
                item.delete()
                message = 'Article supprimé du panier'
            else:
                item.quantity = quantity
                item.save()
                message = 'Quantité mise à jour'
            
            return Response({'success': True, 'message': message})
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Article non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['delete'])
    def clear(self, request):
        """Vider le panier"""
        cart = self.get_cart(request)
        cart.items.all().delete()
        request.session.pop('promo_codes', None)
        return Response({'success': True, 'message': 'Panier vidé'})

class OrderViewSet(viewsets.ModelViewSet):
    """API pour les commandes"""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Annuler une commande"""
        order = self.get_object()
        
        if order.status in ['delivered', 'cancelled']:
            return Response(
                {'error': 'Cette commande ne peut pas être annulée'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'cancelled'
        order.save()
        
        # Rembourser si déjà payé
        if order.is_paid:
            # Logique de remboursement Stripe
            pass
        
        return Response({'success': True, 'message': 'Commande annulée'})
    
    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None):
        """Recommander les mêmes articles"""
        order = self.get_object()
        cart = Cart.objects.get_or_create(user=request.user)[0]
        
        for item in order.items.all():
            if item.lunch_box and item.lunch_box.is_available:
                CartItem.objects.create(
                    cart=cart,
                    lunch_box=item.lunch_box,
                    quantity=item.quantity,
                    customization_notes=item.customization_notes
                )
        
        return Response({
            'success': True,
            'message': 'Articles ajoutés au panier',
            'cart_count': cart.items.count()
        })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_intent(request):
    """Créer une intention de paiement Stripe"""
    cart = Cart.objects.get(user=request.user)
    
    if not cart.items.exists():
        return Response(
            {'error': 'Panier vide'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Récupérer les codes promo
    promo_codes = PromoCode.objects.filter(
        code__in=request.session.get('promo_codes', []),
        is_active=True
    )
    
    totals = calculate_cart_totals(cart, promo_codes)
    
    # Créer l'intention de paiement Stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(totals['total'] * 100),  # En cents
            currency='cad',
            metadata={
                'user_id': request.user.id,
                'cart_id': cart.id
            }
        )
        
        return Response({
            'client_secret': intent.client_secret,
            'total': str(totals['total'])
        })
    except stripe.error.StripeError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Statistiques pour le tableau de bord admin"""
    if not request.user.is_staff:
        return Response(
            {'error': 'Non autorisé'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    
    # Statistiques générales
    stats = {
        'total_orders': Order.objects.count(),
        'total_revenue': Order.objects.aggregate(
            Sum('total_amount')
        )['total_amount__sum'] or 0,
        'total_customers': User.objects.filter(
            orders__isnull=False
        ).distinct().count(),
        'average_order_value': Order.objects.aggregate(
            Avg('total_amount')
        )['total_amount__avg'] or 0,
        
        # Stats du mois
        'monthly_orders': Order.objects.filter(
            created_at__date__gte=thirty_days_ago
        ).count(),
        'monthly_revenue': Order.objects.filter(
            created_at__date__gte=thirty_days_ago
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        
        # Produits populaires
        'top_products': list(OrderItem.objects.values(
            'lunch_box__name'
        ).annotate(
            total_sold=Sum('quantity')
        ).order_by('-total_sold')[:5]),
        
        # Graphique des ventes (30 derniers jours)
        'sales_chart': list(Analytics.objects.filter(
            date__gte=thirty_days_ago
        ).values('date', 'total_revenue', 'total_orders')),
        
        # Commandes récentes
        'recent_orders': list(Order.objects.order_by(
            '-created_at'
        )[:10].values(
            'order_number', 'user__email', 'status', 
            'total_amount', 'created_at'
        )),
        
        # Avis en attente
        'pending_reviews': Review.objects.filter(
            is_approved=False
        ).count(),
        
        # Messages non lus
        'unread_messages': Contact.objects.filter(
            is_read=False
        ).count()
    }
    
    return Response(stats)

@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_stripe(request):
    """Webhook pour les événements Stripe"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    except stripe.error.SignatureVerificationError:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    
    # Gérer l'événement
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        
        # Marquer la commande comme payée
        cart_id = payment_intent['metadata']['cart_id']
        cart = Cart.objects.get(id=cart_id)
        
        # Créer la commande
        # ... (logique de création de commande)
        
    return Response({'received': True})