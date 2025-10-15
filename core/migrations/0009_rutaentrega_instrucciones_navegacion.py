# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_detalleruta_orden_carga_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='rutaentrega',
            name='instrucciones_navegacion',
            field=models.JSONField(blank=True, default=list, help_text='Instrucciones paso a paso de navegación'),
        ),
    ]
