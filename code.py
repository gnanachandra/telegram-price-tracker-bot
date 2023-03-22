from threading import Thread
import requests
import pymongo 
from bs4 import BeautifulSoup
import time
from threading import current_thread
import os
from dotenv import load_dotenv

load_dotenv()
#deleting products that have been price dropped and alert sent to user
welcome_text = "HELLO\nWhat this bot can do ?\n->Send a Amazon product URL followed by target price :)\n->Type 'tracking products' to get the data of products being tracked\n\n /commands to get the list of commands"

headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36"
           ,"Accept-Language":"en"}
base_url = os.getenv('BASE_URL')
mongo_url = os.getenv('MONGO_URI')
print(base_url)


commands_list = '''
/start -> to start the bot
/hi -> replies username
/trackingproducts -> sends the list of tracking products
/help -> email your problem to guestcountforr3@gmail.com
'''


class Message:
    def readMessage(self,offset):
        message = Message()
        product = Product()
        url = URL()
        parameters = {"offset" : offset}
        resp = requests.get(base_url+"/getUpdates",data = parameters)
        data = resp.json()
        print(data)
        for result in  data["result"]:
            try:
                if "/start" in result["message"]["text"]:
                    message.sendMessageToUser(result["message"]["from"]["id"],welcome_text)
                    message.sendMessageToUser(result["message"]["from"]["id"],commands_list)
                elif "/commands" in result["message"]["text"]:
                    message.sendMessageToUser(result["message"]["from"]["id"],commands_list)
                elif "/help" in result["message"]["text"]:
                    message.sendMessageToUser(result["message"]["from"]["id"],"send your email to guestcountforr3@gmail.com")
                elif "hi" == result["message"]["text"].lower():
                    message.sendMessageToUser(result["message"]["from"]["id"],result["message"]["from"]["first_name"])

                elif "https://www.amazon.in/" in result["message"]["text"] or "https://amzn" in result["message"]["text"] :
                    
                    if(len(result["message"]["text"].split(" "))==2):
                      url = result['message']['text'].split(" ")[0]
                      source_code = requests.get(url,headers=headers).text
                      soup = BeautifulSoup(source_code,'lxml')
                      currentPrice = soup.find('span',class_="a-price-whole").text.strip().replace(".","").replace(",","")
                      message.sendDataToUser(result["message"]["from"]["id"],result["message"]["text"])
                      targetPrice = result['message']['text'].split(" ")[1]
                      productName = soup.find('span',class_="a-size-large product-title-word-break").text.strip()
                      if(product.addProduct(result['message']['from']['id'],productName,url,int(currentPrice),int(targetPrice))):
                          message.sendMessageToUser(result['message']['from']['id'],"Product is added to tracking list you will be notified when the price drops to target price")
                      else:
                          message.sendMessageToUser(result['message']['from']['id'],'Unable to add product to tracking list contact Admin')
                          print(data.text)
                    else:
                      message.sendMessageToUser(result['message']['from']['id'],"Target price not received send Amazon link with target price")

                elif "trackingproducts" in result['message']['text']:
                    product.getProductsList(result['message']['from']['id'])
                else :
                    message.sendErrorMessageToUser(result["message"]["from"]["id"])
            except Exception as e:
                print(e)
                message.sendMessageToUser(result["message"]["from"]["id"],"Invalid URL or Price format")
            if data["result"]:
                return data["result"][-1]["update_id"]+1

    def sendMessageToUser(self,chatId,message):
        parameters = {"chat_id":chatId,"text":message}
        data = requests.get(base_url + "/sendMessage",data = parameters)
        print(data.text)
    
    def sendErrorMessageToUser(self,chatId):
        parameters = {"chat_id":chatId,"text":"Invalid Data Received send amazon product link"}
        data = requests.get(base_url + "/sendMessage",data = parameters)
        print(data.text)

    def sendAlertMessageToUser(self,chatId,data,photo_url):
        parameters = {"chat_id":chatId,"photo":photo_url,
                        "caption":data,"protect_content":True}
        data = requests.get(base_url+"/sendPhoto",data = parameters)
        print(data.text)
        thread = current_thread()
        
    
    def sendDataToUser(self,chatId,url_target):
        url = url_target.split(" ")[0]
        product = Product()
       
        targetPrice = url_target.split(" ")[1]
        data,photo_url = product.getProductData(url)
        parameters = {"chat_id":chatId,"photo":photo_url,
                        "caption":data+"\nTarget Price :{0} ".format(targetPrice)}
        data = requests.get(base_url+"/sendPhoto",data = parameters)
        


class Product(Thread):
    def run(self):
        #print('in tracking method')
        url = URL()
        client = pymongo.MongoClient(mongo_url)
        db = client['TrackyDatabase']
        collection = db['TrackData']
        #fetching all data
        message = Message()
        cursor = collection.find({'alert_sent':False})
        for doc in cursor:
            print(doc)
            file= open('demo.html','w')
            product_url = doc['product_url']
            source_code = requests.get(product_url,headers=headers).text
            soup = BeautifulSoup(source_code,'lxml')
            file.write(source_code)
            #print(product_url)
            try:
                productPrice =  soup.find("span", attrs={'class': 'a-price-whole'}).text.replace(".","").replace(",","")
            except:
                productPrice = "Not Available"
            if(productPrice == "Not Available"):
                continue
            #print(productPrice)
            if(int(productPrice) != int(doc['target_price'])):
                productName = soup.find('span',class_="a-size-large product-title-word-break").text.strip()
                productImageLink = soup.find('img',id="landingImage")['src']
                short_url = url.shortenUrl(product_url)
                text = "price dropped for your desired product\n\n"+"product Name : "+ productName+"\n\n"+"Price :"+str(productPrice)+"\n\nBuy Link :"+short_url
                collection.update_one({'_id':doc['_id']},{"$set": { "alert_sent": True }});
                message.sendAlertMessageToUser(doc['chatId'],text,productImageLink)
                #collection.delete_one({"_id":doc['_id']})
       
    def addProduct(self,chatID,productName,productURL,currentPrice,targetPrice):
      url = URL()
      client = pymongo.MongoClient(mongo_url)
      db = client['TrackyDatabase']
      collection = db['TrackData']
      insert_data = {
          "chatId":chatID,
          "product_name":productName,
          "product_url":productURL,
          "current_price":currentPrice,
          "target_price":targetPrice,
          "alert_sent" : False
      }
      try:
        collection.insert_one(insert_data)
        return True
      except :
        return False
      

    def getProductData(self,url):
        source_code = requests.get(url,headers=headers).text
        soup = BeautifulSoup(source_code,'lxml')
        #Getting Product Title
        try:
            productTitle = soup.find("span",attrs={"id": 'productTitle'}).text.strip()
        except AttributeError:
            productTitle = "Not Available"
        #print(productTitle)
        #Getting Product Price
        try:
            productPrice =  int(soup.find("span", attrs={'class': 'a-price-whole'}).text.replace(".","").replace(",",""))
        except AttributeError:
            productPrice = "Not Available"
        #print(productPrice)
        #getting Product Rating
        try:
            rating = soup.find("i", attrs={'class': 'a-icon a-icon-star a-star-4-5'}).string.strip().replace(',', '')
        except AttributeError:
            try:
                rating = soup.find("span", attrs={'class': 'a-icon-alt'}).string.strip().replace(',', '')
            except:
                rating = "NA"
        #print(rating)
        #availabilty Status
        try:
            status = soup.find('div',attrs={'id': 'availability'})
            stock = status.find('span',class_="a-size-medium").text.strip()
        except AttributeError:
            stock = "Not available"
        #print(stock)
        #reviewsCount
        try:
            ratingsCount = soup.find("span", attrs={'id': 'acrCustomerReviewText'}).string.strip().replace(',', '')
        except AttributeError:
            ratingsCount = "Not Available"
        #print(ratingsCount)
        #product Image
        try:
            productImageLink = soup.find('img',id="landingImage")['src']
        except AttributeError:
            productImageLink = "https://img.etimg.com/thumb/msid-59738992,width-640,resizemode-4,imgsize-25499/amazon.jpg"
        return '''
        Product Title : {0}\n\nProduct Price : {1}\n\nproduct Rating : {2}\n\nAvailability Status : {3}\n\nRatings Count : {4}'''.format(productTitle,productPrice,rating,stock,ratingsCount),productImageLink

    def getProductsList(self,chatId):
        url = URL()
        client = pymongo.MongoClient(mongo_url)
        db = client['TrackyDatabase']
        collection = db['TrackData']
        productsList = collection.find({"chatId":chatId})
        #print(productsList)  
        productsData = ""
        for product in productsList:
            #print('In get products data for loop')
            productsData = productsData +"product Name : " + product['product_name'] +"\n\n"+"Product Link :  " + url.shortenUrl(product['product_url']) +"\n\n"
            #print(product['product_url'])
            #print(product['product_name'])
        if(productsData != ""):
            message.sendMessageToUser(chatId,productsData)
        else:
            message.sendMessageToUser(chatId,"No product is being tracked ")

class URL:
    def shortenUrl(self,url):
        username = "o_48ima0r3tl"
        password =  "Guest@bitly"
        auth_res = requests.post("https://api-ssl.bitly.com/oauth/access_token", auth=(username, password))
        if auth_res.status_code == 200:
            access_token = auth_res.content.decode()
            #print("[!] Got access token:", access_token)
        else:
            #print("[!] Cannot get access token, exiting...")
            exit()
        headers = {"Authorization": f"Bearer {access_token}"}
        groups_res = requests.get("https://api-ssl.bitly.com/v4/groups", headers=headers)
        if groups_res.status_code == 200:
            
            groups_data = groups_res.json()['groups'][0]
            guid = groups_data['guid']
            #print(guid)
        else:
            #print("[!] Cannot get GUID, exiting...")
            exit()
        shorten_res = requests.post("https://api-ssl.bitly.com/v4/shorten", json={"group_guid": guid, "long_url": url}, headers=headers)
        if shorten_res.status_code == 200:
            link = shorten_res.json().get("link")
            #print(link)
            return link
        return url


offset = 164700627
while True:
    products = Product()
    message = Message()
    offset = message.readMessage(offset)
    products.start()

#19-03-2023