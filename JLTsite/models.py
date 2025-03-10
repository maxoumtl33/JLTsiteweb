from django.db import models

class CategorieBoiteALunch(models.Model):
    nom = models.CharField(max_length=100)  # Name of the lunch box
    description = models.TextField(max_length=100)  # Description of the lunch box

    def __str__(self):
        return f'{self.nom}'

# Create your models here.
class BoiteALunch(models.Model):
    nom = models.CharField(max_length=100)  # Name of the lunch box
    description = models.TextField()  # Description of the lunch box
    photo1 = models.ImageField(upload_to='photos/', blank=True, null=True)  # First photo
    photo2 = models.ImageField(upload_to='photos/', blank=True, null=True)  # Second photo
    prix =  models.CharField(max_length=100, null=True)
    categorie = models.ForeignKey(CategorieBoiteALunch, on_delete=models.CASCADE, null=True)  # ForeignKey relationship

    def __str__(self):
        return f'{self.nom}'
    



    