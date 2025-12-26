#!/usr/bin/env python3
"""
BAZA License Generator - Interactive Version
Простая генерация лицензионных ключей для BAZA Trading Bot
"""

import base64
import json
import hashlib
from datetime import datetime, timedelta

def generate_license_key(email, expiry_date, license_type="paid"):
    """Генерация лицензионного ключа"""
    data = {
        "email": email,
        "expiry": expiry_date.isoformat(),
        "type": license_type,
        "version": "1.0"
    }

    # Создание хэша для верификации
    data_str = json.dumps(data, sort_keys=True)
    hash_obj = hashlib.sha256(data_str.encode())
    data["hash"] = hash_obj.hexdigest()

    # Кодирование в base64
    json_str = json.dumps(data)
    encoded = base64.b64encode(json_str.encode()).decode()

    return f"BAZA-{encoded}"

def main():
    print("🤖 BAZA License Generator")
    print("=" * 40)

    # Ввод данных
    email = input("Email клиента: ").strip()
    if not email or '@' not in email:
        print("❌ Неверный email!")
        return

    # Выбор срока
    print("\nВыберите срок лицензии:")
    print("1. 1 месяц ($9.99)")
    print("2. 3 месяца ($29.97)")
    print("3. 6 месяцев ($59.94)")
    print("4. 1 год ($99.99)")
    print("5. Другой срок (в месяцах)")

    choice = input("Ваш выбор (1-5): ").strip()

    months = 0
    if choice == '1':
        months = 1
    elif choice == '2':
        months = 3
    elif choice == '3':
        months = 6
    elif choice == '4':
        months = 12
    elif choice == '5':
        try:
            months = int(input("Количество месяцев: ").strip())
        except ValueError:
            print("❌ Неверное число!")
            return
    else:
        print("❌ Неверный выбор!")
        return

    if months <= 0:
        print("❌ Срок должен быть положительным!")
        return

    # Проверка мастер-ключа
    master_key = input("\nМастер-ключ: ").strip()
    if master_key != "BAZA_MASTER_2025":
        print("❌ Неверный мастер-ключ!")
        return

    # Расчет даты истечения
    expiry_date = datetime.now() + timedelta(days=months * 30)

    # Генерация ключа
    license_key = generate_license_key(email, expiry_date)

    # Сохранение в файл
    output_file = f"license_{email.replace('@', '_').replace('.', '_')}.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("BAZA Trading Bot License\n")
        f.write("=" * 40 + "\n")
        f.write(f"Email: {email}\n")
        f.write(f"Срок: {months} месяцев\n")
        f.write(f"Истекает: {expiry_date.strftime('%Y-%m-%d')}\n")
        f.write(f"Ключ: {license_key}\n")
        f.write("\n" + "=" * 40 + "\n")
        f.write("Инструкции:\n")
        f.write("1. Скачайте BAZA с https://github.com/vlvdssss/SMC_bot\n")
        f.write("2. Запустите main.py и введите этот ключ при запросе\n")
        f.write("3. Для поддержки: kamsaaaimpa@gmail.com\n")

    print("\n✅ Лицензия сгенерирована!")
    print(f"📧 Email: {email}")
    print(f"📅 Срок: {months} месяцев (до {expiry_date.strftime('%Y-%m-%d')})")
    print(f"🔑 Ключ: {license_key}")
    print(f"💾 Сохранено в: {output_file}")
    print("\n📤 Отправьте содержимое файла клиенту!")

if __name__ == "__main__":
    main()