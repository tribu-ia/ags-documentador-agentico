import mysql.connector
from bs4 import BeautifulSoup
import re
import dotenv
import json


class MySQLConnector:
    def __init__(self, config):
        self.config = config
        dotenv.load_dotenv()

    def clean_wordpress_content(self, content):
        # Eliminar etiquetas HTML
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()

        # Eliminar atributos de datos de Google Sheets
        text = re.sub(r'data-sheets-[^=]*="[^"]*"', '', text)

        # Eliminar espacios extra y líneas en blanco
        text = re.sub(r'\s+', ' ', text).strip()

        # Eliminar caracteres especiales y mantener solo texto y puntuación básica
        text = re.sub(r'[^\w\s.,;:!?-]', '', text)

        return text

    def get_products_from_db(self):
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor(dictionary=True)


            query = """
            SELECT 
                p.ID, 
                p.post_title, 
                p.post_content,
                pm.max_price AS price,
                GROUP_CONCAT(DISTINCT CASE WHEN tt.taxonomy = 'product_cat' THEN t.name END SEPARATOR ', ') AS categories,
                GROUP_CONCAT(DISTINCT CASE WHEN tt.taxonomy = 'brand' THEN t.name END SEPARATOR ', ') AS brands,
                img1.guid AS thumbnail_url,
                COALESCE(pm_weight.meta_value, '0') AS weight
            FROM 
                wp_posts p
            LEFT JOIN 
                wp_wc_product_meta_lookup pm ON p.ID = pm.product_id
            LEFT JOIN 
                wp_term_relationships tr ON p.ID = tr.object_id
            LEFT JOIN 
                wp_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
            LEFT JOIN 
                wp_terms t ON tt.term_id = t.term_id
            LEFT JOIN 
                wp_postmeta pm_thumb ON p.ID = pm_thumb.post_id AND pm_thumb.meta_key = '_thumbnail_id'
            LEFT JOIN 
                wp_posts img1 ON img1.ID = pm_thumb.meta_value
            LEFT JOIN 
                wp_postmeta pm_weight ON p.ID = pm_weight.post_id AND pm_weight.meta_key = '_weight'
            WHERE 
                p.post_status = 'publish' AND p.post_type = 'product'
            GROUP BY 
                p.ID
            """

            cursor.execute(query)
            products = cursor.fetchall()

            cursor.close()
            conn.close()

            # Limpiar el contenido de cada producto y convertir el precio y peso a float
            for product in products:
                product['post_title'] = self.clean_wordpress_content(product['post_title'])
                product['post_content'] = self.clean_wordpress_content(product['post_content'])
                if product['price'] is not None:
                    product['price'] = float(product['price'])
                product['weight'] = float(product['weight'])

            return products
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return []

    def export_products_to_json(self):
        products = self.get_products_from_db()
        
        formatted_products = {
            "products": []
        }
        
        for product in products:
            formatted_product = {
                "id": product['ID'],
                "title": self.clean_text(product['post_title']),
                "description": self.clean_text(product['post_content']),
                "price": product['price'],
                "categories": [self.clean_text(cat) for cat in product['categories'].split(', ')] if product['categories'] else [],
                "brands": [self.clean_text(brand) for brand in product['brands'].split(', ')] if product['brands'] else [],
                "thumbnail_url": product['thumbnail_url'],
                "weight": product['weight']
            }
            formatted_products["products"].append(formatted_product)
        
        # Guardar en archivo
        with open('products.json', 'w', encoding='utf-8') as f:
            json.dump(formatted_products, f, indent=2, ensure_ascii=False)
        
        # Retornar una versión formateada para imprimir
        return json.dumps(formatted_products, indent=2, ensure_ascii=False)

    def clean_text(self, text):
        if text is None:
            return ""
        # Eliminar saltos de línea y otros caracteres especiales
        text = re.sub(r'\s+', ' ', text)
        # Eliminar caracteres no imprimibles
        text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
        return text.strip()
