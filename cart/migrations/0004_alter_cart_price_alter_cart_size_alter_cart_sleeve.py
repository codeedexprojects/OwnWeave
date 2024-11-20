# Generated by Django 5.1.2 on 2024-10-21 14:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0003_alter_cart_price_alter_cart_quantity_alter_cart_size_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cart',
            name='price',
            field=models.DecimalField(decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='cart',
            name='size',
            field=models.CharField(choices=[('S', 'Small'), ('M', 'Medium'), ('L', 'Large'), ('XL', 'Extra Large'), ('XXL', '2XL'), ('XXXL', '3XL'), ('XXXXL', '4XL'), ('XXXXXL', '5XL')], max_length=6),
        ),
        migrations.AlterField(
            model_name='cart',
            name='sleeve',
            field=models.CharField(choices=[('half', 'Half Sleeve'), ('full', 'Full Sleeve')], max_length=10),
        ),
    ]
