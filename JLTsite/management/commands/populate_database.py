# management/commands/populate_database.py
# Placez ce fichier dans JLTsite/management/commands/populate_database.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify
from decimal import Decimal
from datetime import datetime, timedelta
import random

from JLTsite.models import (
    Category, Product, Order, OrderItem, Cart, CartItem,
    ContactSubmission, User
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Peuple la base de données avec des données de démonstration'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Début du peuplement de la base de données...'))
        
        # Créer les catégories
        self.create_categories()
        
        # Créer les produits
        self.create_products()
        
        # Créer les utilisateurs clients
        self.create_clients()
        
        # Créer les utilisateurs staff
        self.create_staff_users()
        
        # Créer les commandes
        self.create_orders()
        
        # Créer quelques soumissions de contact
        self.create_contact_submissions()
        
        self.stdout.write(self.style.SUCCESS('Base de données peuplée avec succès !'))

    def create_categories(self):
        """Crée les catégories de produits"""
        categories_data = [
            {
                'name': 'Boîtes à lunch',
                'slug': 'boites-a-lunch',
                'description': 'Nos délicieuses boîtes à lunch complètes, parfaites pour vos repas d\'affaires ou événements.',
                'order': 1
            },
            {
                'name': 'Salades',
                'slug': 'salades',
                'description': 'Salades fraîches et variées, préparées avec des ingrédients de qualité.',
                'order': 2
            },
            {
                'name': 'Pâtisserie',
                'slug': 'patisserie',
                'description': 'Nos créations sucrées artisanales pour vos événements spéciaux.',
                'order': 3
            },
            {
                'name': 'Plats chauds',
                'slug': 'plats-chauds',
                'description': 'Plats chauds traditionnels et contemporains pour tous vos événements.',
                'order': 4
            },
            {
                'name': 'Petit-déjeuner',
                'slug': 'petit-dejeuner',
                'description': 'Options de petit-déjeuner pour bien commencer la journée.',
                'order': 5
            },
            {
                'name': 'Sandwichs',
                'slug': 'sandwichs',
                'description': 'Sandwichs artisanaux frais avec des ingrédients de première qualité.',
                'order': 6
            },
            {
                'name': 'Canapés',
                'slug': 'canapes',
                'description': 'Élégants canapés et bouchées pour vos cocktails et réceptions.',
                'order': 7
            }
        ]
        
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                slug=cat_data['slug'],
                defaults=cat_data
            )
            if created:
                self.stdout.write(f'Catégorie créée : {category.name}')

    def create_products(self):
        """Crée les produits pour chaque catégorie"""
        
        # Récupérer les catégories
        categories = {cat.slug: cat for cat in Category.objects.all()}
        
        products_data = [
            # BOÎTES À LUNCH
            {
                'category': 'boites-a-lunch',
                'name': 'Boîte Exécutif - Poulet grillé',
                'description': 'Succulent poulet grillé aux herbes de Provence, accompagné de légumes grillés, riz pilaf et salade verte. Dessert inclus.',
                'ingredients': 'Poulet, légumes de saison, riz, salade verte, vinaigrette, dessert du jour',
                'allergens': 'Gluten, peut contenir des traces de noix',
                'price': Decimal('18.95'),
                'calories': 650,
                'preparation_time': 25,
                'is_featured': True
            },
            {
                'category': 'boites-a-lunch',
                'name': 'Boîte Saumon teriyaki',
                'description': 'Filet de saumon glacé teriyaki, quinoa aux légumes, salade d\'épinards et vinaigrette asiatique.',
                'ingredients': 'Saumon, sauce teriyaki, quinoa, épinards, légumes, vinaigrette',
                'allergens': 'Poisson, soja, gluten',
                'price': Decimal('22.95'),
                'calories': 580,
                'preparation_time': 20
            },
            {
                'category': 'boites-a-lunch',
                'name': 'Boîte Végétarienne Deluxe',
                'description': 'Galette de légumes aux quinoa, houmous maison, taboulé, légumes croquants et pain pita.',
                'ingredients': 'Quinoa, légumes, houmous, taboulé, pain pita',
                'allergens': 'Gluten, sésame',
                'price': Decimal('16.95'),
                'calories': 520,
                'is_vegetarian': True,
                'preparation_time': 15
            },
            {
                'category': 'boites-a-lunch',
                'name': 'Boîte Méditerranéenne',
                'description': 'Brochette de bœuf mariné, couscous aux légumes, salade grecque et tzatziki.',
                'ingredients': 'Bœuf, couscous, légumes méditerranéens, feta, olives, tzatziki',
                'allergens': 'Gluten, produits laitiers',
                'price': Decimal('19.95'),
                'calories': 680,
                'preparation_time': 30
            },
            
            # SALADES
            {
                'category': 'salades',
                'name': 'Salade César aux crevettes',
                'description': 'Salade césar avec crevettes grillées, croûtons maison, parmesan et sauce césar traditionnelle.',
                'ingredients': 'Laitue romaine, crevettes, parmesan, croûtons, sauce césar',
                'allergens': 'Crustacés, gluten, œufs, produits laitiers',
                'price': Decimal('15.95'),
                'calories': 420,
                'preparation_time': 10
            },
            {
                'category': 'salades',
                'name': 'Salade Power Bowl',
                'description': 'Mélange de quinoa, kale, avocat, graines de tournesol, cranberries et vinaigrette au citron.',
                'ingredients': 'Quinoa, kale, avocat, graines, cranberries, vinaigrette citron',
                'allergens': 'Peut contenir des traces de noix',
                'price': Decimal('14.95'),
                'calories': 380,
                'is_vegetarian': True,
                'is_vegan': True,
                'preparation_time': 8
            },
            {
                'category': 'salades',
                'name': 'Salade de chèvre chaud',
                'description': 'Mesclun, tomates cerises, noix, fromage de chèvre chaud sur toast et vinaigrette au miel.',
                'ingredients': 'Mesclun, tomates, noix, fromage de chèvre, pain, miel',
                'allergens': 'Noix, gluten, produits laitiers',
                'price': Decimal('13.95'),
                'calories': 450,
                'is_vegetarian': True,
                'preparation_time': 12
            },
            
            # PÂTISSERIE
            {
                'category': 'patisserie',
                'name': 'Tiramisu individuel',
                'description': 'Tiramisu traditionnel aux biscuits imbibés de café, mascarpone et cacao.',
                'ingredients': 'Mascarpone, café, biscuits, cacao, œufs, sucre',
                'allergens': 'Gluten, œufs, produits laitiers',
                'price': Decimal('6.95'),
                'calories': 320,
                'preparation_time': 5
            },
            {
                'category': 'patisserie',
                'name': 'Tarte au citron meringuée',
                'description': 'Pâte sablée, crème citron onctueuse et meringue italienne légèrement dorée.',
                'ingredients': 'Pâte sablée, citron, œufs, beurre, sucre, meringue',
                'allergens': 'Gluten, œufs, produits laitiers',
                'price': Decimal('5.95'),
                'calories': 280,
                'preparation_time': 45
            },
            {
                'category': 'patisserie',
                'name': 'Éclair au chocolat',
                'description': 'Pâte à choux garnie de crème pâtissière au chocolat et glaçage chocolat noir.',
                'ingredients': 'Pâte à choux, crème pâtissière, chocolat',
                'allergens': 'Gluten, œufs, produits laitiers',
                'price': Decimal('4.95'),
                'calories': 250,
                'preparation_time': 30
            },
            
            # PLATS CHAUDS
            {
                'category': 'plats-chauds',
                'name': 'Lasagne aux légumes',
                'description': 'Lasagne maison aux légumes grillés, sauce béchamel et mozzarella gratinée.',
                'ingredients': 'Pâtes, légumes, sauce tomate, béchamel, mozzarella',
                'allergens': 'Gluten, produits laitiers',
                'price': Decimal('16.95'),
                'calories': 520,
                'is_vegetarian': True,
                'preparation_time': 45
            },
            {
                'category': 'plats-chauds',
                'name': 'Coq au vin traditionnel',
                'description': 'Pièce de poulet mijotée au vin rouge avec champignons, lardons et pommes de terre.',
                'ingredients': 'Poulet, vin rouge, champignons, lardons, pommes de terre',
                'allergens': 'Sulfites',
                'price': Decimal('19.95'),
                'calories': 650,
                'preparation_time': 90
            },
            {
                'category': 'plats-chauds',
                'name': 'Ratatouille provençale',
                'description': 'Légumes du soleil mijotés aux herbes de Provence, accompagnés de riz basmati.',
                'ingredients': 'Courgettes, aubergines, tomates, poivrons, oignons, herbes, riz',
                'allergens': 'Aucun',
                'price': Decimal('14.95'),
                'calories': 380,
                'is_vegetarian': True,
                'is_vegan': True,
                'preparation_time': 60
            },
            
            # PETIT-DÉJEUNER
            {
                'category': 'petit-dejeuner',
                'name': 'Plateau continental',
                'description': 'Viennoiseries, confiture maison, beurre, yaourt, fruits frais et jus d\'orange.',
                'ingredients': 'Croissant, pain au chocolat, confiture, beurre, yaourt, fruits',
                'allergens': 'Gluten, œufs, produits laitiers',
                'price': Decimal('12.95'),
                'calories': 580,
                'preparation_time': 5
            },
            {
                'category': 'petit-dejeuner',
                'name': 'Bol smoothie açaï',
                'description': 'Smoothie açaï avec granola maison, fruits frais et graines de chia.',
                'ingredients': 'Açaï, banane, granola, fruits de saison, graines de chia',
                'allergens': 'Peut contenir des noix',
                'price': Decimal('11.95'),
                'calories': 420,
                'is_vegetarian': True,
                'preparation_time': 8
            },
            {
                'category': 'petit-dejeuner',
                'name': 'Œufs Benedict',
                'description': 'Muffin anglais, jambon de Bayonne, œufs pochés et sauce hollandaise.',
                'ingredients': 'Muffin, jambon, œufs, sauce hollandaise, ciboulette',
                'allergens': 'Gluten, œufs, produits laitiers',
                'price': Decimal('13.95'),
                'calories': 520,
                'preparation_time': 15
            },
            
            # SANDWICHS
            {
                'category': 'sandwichs',
                'name': 'Sandwich Club premium',
                'description': 'Pain de mie grillé, poulet grillé, bacon, avocat, tomate et laitue.',
                'ingredients': 'Pain de mie, poulet, bacon, avocat, tomate, laitue',
                'allergens': 'Gluten',
                'price': Decimal('12.95'),
                'calories': 480,
                'preparation_time': 10
            },
            {
                'category': 'sandwichs',
                'name': 'Panini mozzarella tomate',
                'description': 'Pain ciabatta grillé, mozzarella di buffala, tomates, basilic et huile d\'olive.',
                'ingredients': 'Pain ciabatta, mozzarella, tomates, basilic, huile olive',
                'allergens': 'Gluten, produits laitiers',
                'price': Decimal('10.95'),
                'calories': 420,
                'is_vegetarian': True,
                'preparation_time': 8
            },
            {
                'category': 'sandwichs',
                'name': 'Wrap saumon fumé',
                'description': 'Tortilla aux épinards, saumon fumé, cream cheese, concombre et aneth.',
                'ingredients': 'Tortilla, saumon fumé, cream cheese, concombre, aneth',
                'allergens': 'Gluten, poisson, produits laitiers',
                'price': Decimal('13.95'),
                'calories': 390,
                'preparation_time': 5
            },
            
            # CANAPÉS
            {
                'category': 'canapes',
                'name': 'Canapés saumon gravlax',
                'description': 'Blinis aux saumon gravlax, crème fraîche et aneth (plateau de 12 pièces).',
                'ingredients': 'Blinis, saumon gravlax, crème fraîche, aneth',
                'allergens': 'Gluten, poisson, produits laitiers',
                'price': Decimal('24.95'),
                'calories': 180,
                'preparation_time': 20
            },
            {
                'category': 'canapes',
                'name': 'Bouchées de foie gras',
                'description': 'Toast briochés, foie gras mi-cuit et confit d\'oignons (plateau de 8 pièces).',
                'ingredients': 'Pain brioché, foie gras, confit d\'oignons',
                'allergens': 'Gluten, œufs, produits laitiers',
                'price': Decimal('35.95'),
                'calories': 220,
                'preparation_time': 25
            },
            {
                'category': 'canapes',
                'name': 'Verrines apéritives',
                'description': 'Assortiment de verrines: houmous, guacamole, tartare de légumes (plateau de 15 pièces).',
                'ingredients': 'Légumes variés, houmous, avocat, épices',
                'allergens': 'Sésame',
                'price': Decimal('18.95'),
                'calories': 120,
                'is_vegetarian': True,
                'preparation_time': 30
            }
        ]
        
        for product_data in products_data:
            category_slug = product_data.pop('category')
            category = categories.get(category_slug)
            
            if category:
                product_data['category'] = category
                product_data['slug'] = slugify(product_data['name'])
                product_data['stock'] = random.randint(10, 50)
                
                # CORRECTION: Convertir le float en Decimal pour le calcul
                if random.choice([True, False]):
                    discount = Decimal(str(random.uniform(0.05, 0.20)))
                    product_data['promo_price'] = product_data['price'] * (Decimal('1') - discount)
                
                product, created = Product.objects.get_or_create(
                    slug=product_data['slug'],
                    defaults=product_data
                )
                
                if created:
                    self.stdout.write(f'Produit créé : {product.name}')

    def create_clients(self):
        """Crée des utilisateurs clients"""
        clients_data = [
            {
                'username': 'marie.dubois',
                'email': 'marie.dubois@gmail.com',
                'first_name': 'Marie',
                'last_name': 'Dubois',
                'phone': '514-123-4567',
                'company': 'TechnoSoft Inc.',
                'address': '1234 Rue Saint-Denis, Montréal, QC',
                'postal_code': 'H2X 3K2',
                'city': 'Montréal'
            },
            {
                'username': 'jean.martin',
                'email': 'j.martin@corporate.ca',
                'first_name': 'Jean',
                'last_name': 'Martin',
                'phone': '514-234-5678',
                'company': 'Martin & Associés',
                'address': '5678 Boulevard Saint-Laurent, Montréal, QC',
                'postal_code': 'H2T 1S1',
                'city': 'Montréal'
            },
            {
                'username': 'sophie.tremblay',
                'email': 'sophie.t@design.qc.ca',
                'first_name': 'Sophie',
                'last_name': 'Tremblay',
                'phone': '514-345-6789',
                'company': 'Studio Créatif',
                'address': '9012 Rue Rachel Est, Montréal, QC',
                'postal_code': 'H1W 3V4',
                'city': 'Montréal'
            },
            {
                'username': 'pierre.levesque',
                'email': 'p.levesque@avocat.ca',
                'first_name': 'Pierre',
                'last_name': 'Lévesque',
                'phone': '514-456-7890',
                'company': 'Cabinet Lévesque',
                'address': '3456 Rue Sherbrooke Ouest, Montréal, QC',
                'postal_code': 'H3A 1B9',
                'city': 'Montréal'
            },
            {
                'username': 'isabelle.roy',
                'email': 'isabelle.roy@gmail.com',
                'first_name': 'Isabelle',
                'last_name': 'Roy',
                'phone': '514-567-8901',
                'company': 'Freelance',
                'address': '7890 Avenue du Parc, Montréal, QC',
                'postal_code': 'H2V 4E2',
                'city': 'Montréal'
            },
            {
                'username': 'francois.gagnon',
                'email': 'f.gagnon@medecin.ca',
                'first_name': 'François',
                'last_name': 'Gagnon',
                'phone': '514-678-9012',
                'company': 'Clinique Santé Plus',
                'address': '2345 Rue Jean-Talon, Montréal, QC',
                'postal_code': 'H2R 1W8',
                'city': 'Montréal'
            }
        ]
        
        for client_data in clients_data:
            if not User.objects.filter(username=client_data['username']).exists():
                user = User.objects.create_user(
                    username=client_data['username'],
                    email=client_data['email'],
                    password='password123',
                    first_name=client_data['first_name'],
                    last_name=client_data['last_name']
                )
                
                # Ajouter les champs supplémentaires s'ils existent
                for field, value in client_data.items():
                    if hasattr(user, field) and field not in ['username', 'email', 'first_name', 'last_name']:
                        setattr(user, field, value)
                
                user.role = 'customer'
                user.save()
                
                self.stdout.write(f'Client créé : {user.get_full_name()}')

    def create_staff_users(self):
        """Crée les utilisateurs du personnel"""
        staff_data = [
            {
                'username': 'chef.principal',
                'email': 'chef@jlt.com',
                'first_name': 'Antoine',
                'last_name': 'Dubois',
                'role': 'head_chef'
            },
            {
                'username': 'chef.patisserie',
                'email': 'patisserie@jlt.com',
                'first_name': 'Marie',
                'last_name': 'Leclerc',
                'role': 'department_chef'
            },
            {
                'username': 'chef.chaud',
                'email': 'chaud@jlt.com',
                'first_name': 'Philippe',
                'last_name': 'Rousseau',
                'role': 'department_chef'
            },
            {
                'username': 'cuisinier1',
                'email': 'cuisinier1@jlt.com',
                'first_name': 'Marc',
                'last_name': 'Turcotte',
                'role': 'cook'
            },
            {
                'username': 'cuisinier2',
                'email': 'cuisinier2@jlt.com',
                'first_name': 'Sarah',
                'last_name': 'Bélanger',
                'role': 'cook'
            }
        ]
        
        for staff in staff_data:
            if not User.objects.filter(username=staff['username']).exists():
                user = User.objects.create_user(
                    username=staff['username'],
                    email=staff['email'],
                    password='password123',
                    first_name=staff['first_name'],
                    last_name=staff['last_name'],
                    role=staff['role']
                )
                self.stdout.write(f'Personnel créé : {user.get_full_name()} ({user.role})')

    def create_orders(self):
        """Crée des commandes d'exemple"""
        clients = User.objects.filter(role='customer')
        products = list(Product.objects.all())
        
        if not clients.exists() or not products:
            self.stdout.write(self.style.WARNING('Pas assez de clients ou produits pour créer des commandes'))
            return
        
        # Créer des commandes pour les 30 derniers jours
        for i in range(25):
            client = random.choice(clients)
            
            # Date de commande dans les 30 derniers jours
            order_date = timezone.now() - timedelta(days=random.randint(0, 30))
            
            # Date de livraison 1-7 jours après la commande
            delivery_date = order_date.date() + timedelta(days=random.randint(1, 7))
            delivery_time = datetime.strptime(random.choice(['11:30', '12:00', '12:30', '18:00', '18:30']), '%H:%M').time()
            
            # Créer la commande
            order = Order.objects.create(
                user=client,
                first_name=client.first_name,
                last_name=client.last_name,
                email=client.email,
                phone=getattr(client, 'phone', '514-123-4567'),
                company=getattr(client, 'company', ''),
                delivery_type=random.choice(['delivery', 'pickup']),
                delivery_address=getattr(client, 'address', '1234 Rue Example, Montréal, QC'),
                delivery_postal_code=getattr(client, 'postal_code', 'H1A 1A1'),
                delivery_city=getattr(client, 'city', 'Montréal'),
                delivery_date=delivery_date,
                delivery_time=delivery_time,
                status=random.choice(['pending', 'confirmed', 'preparing', 'ready', 'delivered']),
                created_at=order_date,
                subtotal=Decimal('0'),
                tax_amount=Decimal('0'),
                total=Decimal('0')
            )
            
            # Ajouter des articles à la commande
            num_items = random.randint(1, 4)
            order_total = Decimal('0')
            
            for _ in range(num_items):
                product = random.choice(products)
                quantity = random.randint(1, 3)
                price = product.get_price()
                subtotal = price * quantity
                
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    product_price=price,
                    quantity=quantity,
                    subtotal=subtotal,
                    department=self.assign_department_from_category(product.category.name)
                )
                
                order_total += subtotal
            
            # Mettre à jour les totaux de la commande
            order.subtotal = order_total
            order.tax_amount = order_total * (order.tax_rate / 100)
            order.total = order.subtotal + order.tax_amount
            order.save()
            
            if i % 5 == 0:
                self.stdout.write(f'Commande créée : {order.order_number} pour {client.get_full_name()}')

    def assign_department_from_category(self, category_name):
        """Assigne un département basé sur la catégorie"""
        mapping = {
            'Boîtes à lunch': 'boites',
            'Salades': 'salades',
            'Pâtisserie': 'patisserie',
            'Plats chauds': 'chaud',
            'Petit-déjeuner': 'dejeuners',
            'Sandwichs': 'sandwichs',
            'Canapés': 'bouchees'
        }
        return mapping.get(category_name, 'autres')

    def create_contact_submissions(self):
        """Crée des soumissions de contact"""
        submissions_data = [
            {
                'first_name': 'Sylvie',
                'last_name': 'Bouchard',
                'email': 'sylvie.bouchard@entreprise.ca',
                'phone': '514-987-6543',
                'company': 'Bouchard & Fils',
                'event_type': 'corporate',
                'guest_count': 50,
                'event_date': timezone.now().date() + timedelta(days=45),
                'budget': '2500-5000',
                'message': 'Nous organisons notre party de Noël d\'entreprise et cherchons un traiteur pour un événement corporatif élégant.'
            },
            {
                'first_name': 'Michael',
                'last_name': 'Thompson',
                'email': 'michael.t@wedding.com',
                'phone': '514-876-5432',
                'company': '',
                'event_type': 'wedding',
                'guest_count': 120,
                'event_date': timezone.now().date() + timedelta(days=180),
                'budget': '>10000',
                'message': 'Mariage prévu pour l\'été prochain. Nous recherchons un service de qualité pour notre réception.'
            },
            {
                'first_name': 'Nathalie',
                'last_name': 'Grenier',
                'email': 'n.grenier@cocktail.ca',
                'phone': '514-765-4321',
                'company': 'Events & Co',
                'event_type': 'cocktail',
                'guest_count': 80,
                'event_date': timezone.now().date() + timedelta(days=21),
                'budget': '1000-2500',
                'message': 'Cocktail d\'inauguration pour notre nouvelle boutique. Nous avons besoin de canapés et boissons.'
            }
        ]
        
        for submission_data in submissions_data:
            ContactSubmission.objects.create(**submission_data)
            self.stdout.write(f'Soumission de contact créée : {submission_data["first_name"]} {submission_data["last_name"]}')

        self.stdout.write(self.style.SUCCESS(f'{len(submissions_data)} soumissions de contact créées'))
