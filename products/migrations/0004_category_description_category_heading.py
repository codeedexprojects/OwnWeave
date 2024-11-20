# Generated by Django 5.1.2 on 2024-11-02 09:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0003_category_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="category",
            name="heading",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]