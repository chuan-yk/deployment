from django.db import models

# Create your models here.
class Order (models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    delivery_date = models.DateField(blank=True)
    product_id = models.TextField()
    payment_option = models.CharField(max_length=50)
    amount = models.IntegerField()
    order_status = models.CharField(max_length=50)


class uploadlist (models.Model):
    platform = models.CharField(max_length=20)
    app = models.CharField(max_length=200)
    user = models.CharField(max_length=100)
    filename = models.CharField(max_length=300)
    bug_id = models.IntegerField()
    file_path = models.CharField(max_length=300)
    description = models.CharField(max_length=500)
    status = models.IntegerField()
    upload_date = models.DateField()