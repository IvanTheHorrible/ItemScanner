import flask, json, requests
from flask import request, jsonify

app = flask.Flask(__name__)

mobile_headers = {
          "user-agent": "Popspedia/28 CFNetwork/978.0.7 Darwin/18.7.0",
          "content-type": "application/json",
          "cache-control": "no-cache",
          "accept-encoding": "gzip, deflate, br",
          "accept-language": "en-US"
        }

web_headers = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36",
    "cache-control": "no-cache"
}

def productDetails(upc):
    target_product_title, target_product_link, target_product_picture, target_relatedItems = targetAPI(upc)
    walmart_product_title, walmart_product_link, walmart_product_picture, walmart_relatedItems = walmartAPI(upc)
    product = {}
    if target_product_title:
        product['productTitle'] = target_product_title
    if not product['productTitle'] and walmart_product_title:
        product['productTitle'] = walmart_product_title
    if target_product_picture:
        product['productPic'] = target_product_picture
    if not product['productPic'] and walmart_product_picture:
        product['productPic'] = walmart_product_picture
    productLinks = []
    if target_product_link:
        productLinks.append(
            {
                'store': 'target',
                'link': target_product_link
            }
        )
    if walmart_product_link:
        productLinks.append(
            {
                'store': 'walmart',
                'link': walmart_product_link
            }
        )
    
    product['productLinks'] = productLinks

    if target_relatedItems:
        product['relatedItems'] = target_relatedItems

    if walmart_relatedItems and product['relatedItems']:
        product['relatedItems'] += walmart_relatedItems

    return product

def targetAPI(upc):
    target_api_url = "https://redsky.target.com/v4/products/pdp/BARCODE/{}/3284?key=3f015bca9bce7dbb2b377638fa5de0f229713c78&pricing_context=digital&pricing_store_id=3284"
    r0 = requests.get(target_api_url.format(upc), headers=mobile_headers)
    try:
        product = r0.json()['products'][0]
        target_product_title = product['title']
        target_product_link = product['targetDotComUri']
        target_product_picture = product['images']['primaryUri']
        target_tcin = product['tcin']
        target_relatedItems = targetRelatedProducts(target_tcin)
        return target_product_title, target_product_link, target_product_picture, target_relatedItems
    except:
        return '','','',[]

def walmartAPI(upc):
    walmart_api_url = "https://search.mobile.walmart.com/v1/products-by-code/UPC/{}?storeId=3520"
    r0 = requests.get(walmart_api_url.format(upc), headers=mobile_headers)
    try:
        product = r0.json()['data']['common']
        walmart_product_title = product['name']
        walmart_product_link = product['productUrl']
        walmart_product_picture = product['productImageUrl']
        relatedItemsUrl = r0.json()['data']['relatedItemsUrls']['online']
        walmart_relatedItems = walmartRelatedProducts(relatedItemsUrl)
        return walmart_product_title, walmart_product_link, walmart_product_picture, walmart_relatedItems
    except:
        return '','','',[]
    
def walmartRelatedProducts(url):
    query_url = 'https://search.mobile.walmart.com' + url
    r0 = requests.get(query_url, headers=mobile_headers)
    try:
        items = r0.json()['item']
        relatedItems = []
        foundrelatedItems = False
        i = 0
        relatedCount = 0
        while not foundrelatedItems:
            if relatedCount == 2:
                foundrelatedItems = True
            if items[i]['addableToCart']:
                productName = str(items[i]['name']).replace('<mark>', '').replace('</mark>', '')
                relatedItems.append({
                    'productName' : productName,
                    'productImage' : items[i]['productImageUrl'],
                    'store': 'walmart',
                    'productSku' : items[i]['iD']    
                })
                relatedCount += 1
            i += 1
        return relatedItems
    except Exception as e:
        print('Error: ' + str(e))
        return []

def targetRelatedProducts(sku):
    query_url = 'https://redsky.target.com/recommended_products/v1?tcins={}&placement_id=adaptpdph1&pricing_store_id=3284&store_id=3284&purchasable_store_ids=3284%2C3249%2C3229%2C2850%2C3321&visitor_id=017031967BE90201B2A1FC53191E7DF5&key=eb2551e4accc14f38cc42d32fbc2b2ea'.format(sku)
    r0 = requests.get(query_url, headers=web_headers)
    try:
        items = r0.json()['products']
        relatedItems = []
        foundrelatedItems = False
        i = 0
        relatedCount = 0
        while not foundrelatedItems:
            if relatedCount == 3:
                foundrelatedItems = True
            if items[i]['availability_status'] == 'IN_STOCK':
                relatedItems.append({
                    'productName' : items[i]['title'],
                    'productImage' : items[i]['primary_image_url'],
                    'store': 'target',
                    'productSku' : items[i]['tcin']    
                })
                relatedCount += 1
            i += 1
        return relatedItems
    except Exception as e:
        print('Error: ' + str(e))
        return []

def fetchItemInfo(store, sku):
    try:
        upc = ''
        if store == 'target':
            query_url = 'https://redsky.target.com/v2/pdp/tcin/{}?excludes=promotion,taxonomy,bulk_ship,awesome_shop,question_answer_statistics,rating_and_review_reviews,rating_and_review_statistics,deep_red_labels'.format(sku)
            r0 = requests.get(query_url, headers=web_headers)
            item = r0.json()['product']['item']
            upc = item['upc']
        elif store == 'walmart':
            query_url = 'https://www.walmart.com/terra-firma/item/{}'.format(sku)
            r0 = requests.get(query_url, headers=web_headers)
            products = r0.json()['payload']['products']
            for product in products:
                upc = products[product]['upc']
        print(upc)
        return upc
    except Exception as e:
        print('Error: ' + str(e))
        return ''
    
def queryTarget(query):
    try:
        query_url = 'https://redsky.target.com/v4/products/list/3284?key=3f015bca9bce7dbb2b377638fa5de0f229713c78&limit=10&pageNumber=1&pricing_context=digital&pricing_store_id=3284&searchTerm={}'
        r0 = requests.get(query_url.format(query), headers=mobile_headers)
        query_products = r0.json()['products']
        products = []
        for product in query_products:
            products.append({
                'productName': product['title'],
                'productImage': product['images']['primaryUri'],
                'productUpc': product['upc']
            })
        return products

    except Exception as e:
        print('Error: ' + str(e))
        return []

@app.route('/', methods=['GET'])
def index():
    return "<h1>Welcome to our server !!</h1>"
    
@app.route('/api/v1/productdetails', methods=['GET'])
def api_all():
    query_parameters = request.args

    upc = query_parameters.get('upc')

    results = productDetails(upc)
    return jsonify(results)

@app.route('/api/v1/productinfo', methods=['GET'])
def api_sku():
    query_parameters = request.args

    store = query_parameters.get('store')
    sku = query_parameters.get('sku')

    upc = fetchItemInfo(store, sku)
    results = productDetails(upc)
    return jsonify(results)

@app.route('/api/v1/products/list', methods=['GET'])
def api_query():
    query_parameters = request.args

    query = query_parameters.get('searchTerm')

    products = queryTarget(query)
    return jsonify(products)

if __name__ == '__main__':
    app.run()
