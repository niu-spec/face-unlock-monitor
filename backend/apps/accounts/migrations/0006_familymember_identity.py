from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_add_dingtalk_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="familymember",
            name="identity",
            field=models.CharField(blank=True, default="", max_length=32, verbose_name="身份"),
        ),
    ]
