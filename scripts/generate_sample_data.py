#!/usr/bin/env python3
"""
Generate sample sales data for SmartInventory demo and testing
"""

import os
import sys
import django
import csv
import math
import random
from datetime import datetime, timedelta, date
from decimal import Decimal

# Setup Django environment (works both locally and in Docker)
# Add project root (parent of this "scripts" folder) to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartinventory.settings')
django.setup()

from apps.core.models import Store, Product
from apps.data_management.models import SalesData


def generate_stores(num_stores=10):
    """Generate sample stores"""
    stores = []
    for i in range(1, num_stores + 1):
        store_id = f"STORE{i:03d}"
        store, created = Store.objects.get_or_create(
            store_id=store_id,
            defaults={
                'name': f"Store {i}",
                'location': f"City {i}, State {i % 5 + 1}",
                'is_active': True
            }
        )
        stores.append(store)
        if created:
            print(f"Created store: {store_id}")

    return stores


def generate_products(num_products=50):
    """Generate sample products"""
    categories = ['Electronics', 'Clothing', 'Home', 'Sports', 'Books', 'Toys']
    brands = ['BrandA', 'BrandB', 'BrandC', 'BrandD', 'BrandE']

    products = []
    for i in range(1, num_products + 1):
        sku_id = f"SKU{i:04d}"
        product, created = Product.objects.get_or_create(
            sku_id=sku_id,
            defaults={
                'name': f"Product {i}",
                'category': random.choice(categories),
                'brand': random.choice(brands),
                'is_active': True
            }
        )
        products.append(product)
        if created:
            print(f"Created product: {sku_id}")

    return products


def generate_sales_data(stores, products, days=365):
    """Generate historical sales data"""
    print(f"Generating sales data for {days} days...")

    start_date = date.today() - timedelta(days=days)
    created_count = 0
    batch_size = 1000
    batch = []

    for day_offset in range(days):
        current_date = start_date + timedelta(days=day_offset)

        # Skip some days randomly to simulate realistic data gaps
        if random.random() < 0.05:  # 5% chance of no sales
            continue

        # Generate seasonal patterns
        day_of_year = current_date.timetuple().tm_yday
        seasonal_multiplier = 1 + 0.3 * math.sin(2 * math.pi * day_of_year / 365)

        # Weekend effect
        weekend_multiplier = 1.2 if current_date.weekday() >= 5 else 1.0

        for store in stores:
            # Each store sells subset of products
            store_products = random.sample(products, random.randint(20, 40))

            for product in store_products:
                # Skip some product-store combinations randomly
                if random.random() < 0.3:
                    continue

                # Generate base sales pattern
                base_sales = random.uniform(1, 20)

                # Apply seasonal and weekend effects
                sales = base_sales * seasonal_multiplier * weekend_multiplier

                # Add some randomness
                sales += random.gauss(0, 2)
                sales = max(0, sales)  # Ensure non-negative

                # Generate price with some variation
                base_price = random.uniform(10, 100)
                price_variation = random.uniform(0.9, 1.1)
                price = base_price * price_variation

                # Promotions (10% chance)
                promotions_flag = random.random() < 0.1
                if promotions_flag:
                    sales *= random.uniform(1.2, 1.8)  # Promotion boost
                    price *= random.uniform(0.8, 0.95)  # Discount

                # Inventory levels
                on_hand = random.randint(0, 200)

                # Create sales record
                sales_data = SalesData(
                    store=store,
                    product=product,
                    date=current_date,
                    sales=Decimal(str(round(sales, 2))),
                    price=Decimal(str(round(price, 2))),
                    on_hand=on_hand,
                    promotions_flag=promotions_flag
                )

                batch.append(sales_data)

                # Bulk create when batch is full
                if len(batch) >= batch_size:
                    try:
                        SalesData.objects.bulk_create(batch, ignore_conflicts=True)
                        created_count += len(batch)
                        print(f"Created {created_count} sales records...")
                        batch = []
                    except Exception as e:
                        print(f"Error creating batch: {e}")
                        batch = []

    # Create remaining records
    if batch:
        try:
            SalesData.objects.bulk_create(batch, ignore_conflicts=True)
            created_count += len(batch)
        except Exception as e:
            print(f"Error creating final batch: {e}")

    print(f"Total sales records created: {created_count}")
    return created_count


def export_sample_csv(filename='sample_sales_data.csv', num_records=1000):
    """Export sample data to CSV file"""
    print(f"Exporting {num_records} sample records to {filename}...")

    # Get some sample data
    sample_data = SalesData.objects.select_related('store', 'product')[:num_records]

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)

        # Write header
        writer.writerow([
            'date', 'store_id', 'sku_id', 'sales', 'price',
            'on_hand', 'promotions_flag'
        ])

        # Write data
        for record in sample_data:
            writer.writerow([
                record.date.strftime('%Y-%m-%d'),
                record.store.store_id,
                record.product.sku_id,
                float(record.sales),
                float(record.price),
                record.on_hand,
                1 if record.promotions_flag else 0
            ])

    print(f"Sample CSV exported to {filename}")


def main():
    """Main function to generate all sample data"""
    print("Starting sample data generation...")

    # Generate stores and products
    stores = generate_stores(num_stores=10)
    products = generate_products(num_products=50)

    print(f"Generated {len(stores)} stores and {len(products)} products")

    # Generate sales data for last year
    sales_count = generate_sales_data(stores, products, days=365)

    # Export sample CSV
    export_sample_csv('sample_sales_data.csv', num_records=1000)

    print("\nSample data generation completed!")
    print(f"- {len(stores)} stores")
    print(f"- {len(products)} products")
    print(f"- {sales_count} sales records")
    print("- sample_sales_data.csv exported for demo uploads")


if __name__ == '__main__':
    main()