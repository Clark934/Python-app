# coding: utf-8
#!/usr/bin/env python
"""Provides a web scraping tool for homedepot.com, including a search engine and a crawler.

The homedepot_site_map class grab the hierarchical department structure from site-map by generating a nested dictionary.
The homedepot_crawler class is built to scrape product information from sepecific department, sub_department, brand 
and location and store the result to a dataframe.
"""

__author__ = "Siyao Chen"
__email__ = "schen245@fordham.edu"


import re,requests,random
import ast
import urllib.request
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import time
import re
from fake_useragent import UserAgent
from fake_useragent import FakeUserAgentError
import math
from selenium import webdriver
from selenium.webdriver.common.keys import Keys



# The purpose of this class is to build a search engine (nested dictionary) to get the source url -
# -for specific sub_department and department. It also grab the hierarchical department structure from site-map -
# -by generating a nested dictionary. An example usage of the output dictionary is like this:
# [In]: dep_dict["Furniture"]["Bedroom Furniture"]["Mattresses"]
# [Out]: 'https://www.homedepot.com/b/Furniture-Bedroom-Furniture-Mattresses/N-5yc1vZc7oe'
# [In]: dep_dict["Furniture"]["Bedroom Furniture"]['Nightstands']
# [Out]:'https://www.homedepot.com/b/Furniture-Bedroom-Furniture-Nightstands/N-5yc1vZceum'
class homedepot_site_map:
    
    def __init__(self):
        self.url = 'https://www.homedepot.com/c/site_map'
    # Using the site-map of the website as source url.
    
    def get_random_header(self):
        '''Get random user agents(headers)'''
        ua = UserAgent()
        ua.update()
        return ua

    # I use parse_gp() and gatherproxy_resp() to grab free proxies(IP addresses) to build my own proxy-pool -
    # -to defend the anti-crawler of the website.
    def parse_gp(self, lines):
        ''' Parse the raw scraped data for proxy-pool'''
        gatherproxy_list = []
        for l in lines:
            if 'proxy_ip' in l.lower():
                l = l.replace('gp.insertPrx(', '')
                l = l.replace(');', '')
                l = l.replace('null', 'None')
                l = l.strip()
                l = ast.literal_eval(l)

                proxy = '{}:{}'.format(l["PROXY_IP"], l["PROXY_PORT"])
                gatherproxy_list.append(str(proxy))
        return gatherproxy_list
    
    # Gatherproxy.com provides us free proxies for scraping. We just need to scrape the list and store into a list.
    def gatherproxy_resp(self):
        url = 'http://gatherproxy.com/proxylist/anonymity/?t=Elite'
        header={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)                AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'}
        try:
            r = requests.get(url, headers = header)
            lines = r.text.splitlines()
        except:
            gatherproxy_list = []
            return gatherproxy_list

        gatherproxy_list = self.parse_gp(lines)
        return gatherproxy_list
    
    # Built my own get_html() function to get respond of a web page and parse the html file.
    def get_html(self, url):
        try:
            header = {'User-Agent':ua.random} 
        except:
            header={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)        AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'}
        # If connection failed using one of the proxy, we'll reconnect for 4 times using other proxies.
        retry_count = 5
        while retry_count > 0:
            try:
                # Pass in proxies and headers to request module to confuse anti-crawler.
                request= requests.get(url, proxies={'http':'http://'+ random.choice(gatherproxy_resp())},headers = header)
                html = request.text
                #Bs4 can use different HTML parsers, each of which has its advantages and disadvantages.
                #The default is to use Python's integrated HTML parser in the html.parser module.
                #lxml module is better for websites with dynamic elements.
                soup = BeautifulSoup(html, 'lxml')
                return soup
            except Exception:
                retry_count -= 1
        request= requests.get(url, headers = header)
        html = request.text
        soup = BeautifulSoup(html, 'lxml')
        return soup
    
    #I used get_dep_dict() to crawl links and names of departmens, and built a nested dictionary to store the result.
    #There're two levels in the dictionary for now. The first level is department level; the second is sub_department.
    #For example, we can pass in the department and sub_department name to grab the corresponding link for it.
    #[In]: dep_dict["Appliances"]['Dishwashers']
    #[Out]: 'https://www.homedepot.com/b/Appliances-Dishwashers/N-5yc1vZc3po'
    #But for some special cases like "Furniture" ("Bedroom Furniture"), we have to add a level to our dict.
    def get_dep_dict(self, url): 
        soup = self.get_html(url)
        department_all_raw = soup.find_all('ul', attrs= {"class": "list list--type-plain u__text-align--left "})[:29]
        dep_sub_name_all = []
        dep_sub_link_all = []
        for i in department_all_raw:
            dep_sub_name = []
            dep_sub_link = []
            for j in i.find_all('li', {"class": "list__item list__item--padding-none "}):
                if j.text.strip() != "":
                    dep_sub_name.append(j.text.strip())
                    try:
                        dep_sub_link.append(j.find('a').attrs['href'])
                    except:
                        dep_sub_link.append("")
            dep_sub_name_all.append(dep_sub_name)
            dep_sub_link_all.append(dep_sub_link)
            
        dep_name = []
        for i in dep_sub_name_all:
            dep_name.append(i[0])
        
        sub_dict_ls = list(map(dict, map(zip, dep_sub_name_all, dep_sub_link_all)))
        #[dict(zip(*z)) for z in zip(dep_sub_name_all, dep_sub_link_all)]
        dep_dict = dict(zip (dep_name, sub_dict_ls))
        return dep_dict
    
    # For "Furniture" department, there're three levels: "Furniture" -> "Bedroom Furniture" -> "Matresses"
    # So I use the link for "Bedroom Furniture" to crawl its sub_department and update the nested dict in the level 2.
    #The final dict looks like this:
    # [In]: dep_dict["Furniture"]["Bedroom Furniture"]["Mattresses"]
    # [Out]: 'https://www.homedepot.com/b/Furniture-Bedroom-Furniture-Mattresses/N-5yc1vZc7oe'
    def run(self):
        dep_dict = self.get_dep_dict(self.url)
        url_current = dep_dict["Furniture"]["Bedroom Furniture"]
        soup = self.get_html(url_current)
        dep_sub_2_ls_raw = soup.find('ul', attrs={"data-refinement": "Department"})
        dep_sub_2_name = [i.find('a').text.strip().split("(")[0].strip() for i in dep_sub_2_ls_raw .find_all('li')]
        dep_sub_2_name.pop(0)
        dep_sub_2_link = ["https://www.homedepot.com" + i.find('a').attrs["href"] for i in dep_sub_2_ls_raw .find_all('li')]
        dep_sub_2_link.pop(0)
        dep_dict["Furniture"]["Bedroom Furniture"] = dict(zip (dep_sub_2_name, dep_sub_2_link))
        return dep_dict
    


# This class is built to scrape product information from sepecific department, sub_department, brand and location.
# The output of the class is a dataframe with the following collumns with each row as a single product shown below:
# Department--Sub Department--Current price--Price saving--Brand--Description--Product link--Location
# Appliances--Dishwashers--549.0--150.0--LG Electronics--Front Control Tall-Tub Dishwasher in Stain...--https://www.homedepot.com/p/LG-Electronics-Fro...--75209
# If nothing is on display in the sepecific location, the dataframe will add a row with description as - 
# -"No items on display"
# The proxy-pool method will be inherited from homedepot_site_map.
# In this class, I'll also demonstrate how I crawl data from multiple pages using Bs4 and how I deal with -
# -the "load more" button using selenium.

class homedepot_crawler(homedepot_site_map):
    
    # __init__ method here will pass in the department, sub_department, brand, location information from instances of the class.
    def __init__(self, department, sub_department, brand, location):
        self.department = department#.replace(" ", "-").lower()
        self.sub_department = sub_department#.lower()
        self.brand = brand.lower()
        self.location = location
        #The cookies are collected from the website to determine the specific store we want to crawl by passing in requests.
        self.cookies = {10022: dict(THD_PERSIST='C4%3D6177%2BManhattan%2059th%20Street%20-%20New%20York%2C%20NY%2B%3A%3BC4_EXP%3D1572030922%3A%3BC24%3D10022%3A%3BC24_EXP%3D1572030922%3A%3BC34%3D32.1%3A%3BC34_EXP%3D1540582116%3A%3BC39%3D1%3B8%3A00-20%3A00%3B2%3B7%3A00-22%3A00%3B3%3B7%3A00-22%3A00%3B4%3B7%3A00-22%3A00%3B5%3B7%3A00-22%3A00%3B6%3B7%3A00-22%3A00%3B7%3B7%3A00-22%3A00%3A%3BC39_EXP%3D1540498522'),
                  75209: dict(THD_PERSIST='C4%3D589%2BLemmon%20Ave%20-%20Dallas%2C%20TX%2B%3A%3BC4_EXP%3D1572032392%3A%3BC24%3D75209%3A%3BC24_EXP%3D1572032392%3A%3BC34%3D32.1%3A%3BC34_EXP%3D1540582829%3A%3BC39%3D1%3B8%3A00-20%3A00%3B2%3B6%3A00-22%3A00%3B3%3B6%3A00-22%3A00%3B4%3B6%3A00-22%3A00%3B5%3B6%3A00-22%3A00%3B6%3B6%3A00-22%3A00%3B7%3B6%3A00-22%3A00%3A%3BC39_EXP%3D1540499992')}

    # Using the search enginee(dep_dict) built above, we can pass in the department and sub_department name to get -
    # - url for further crawling (brands).
    def get_source_url(self):

        if self.department == 'Bedroom Furniture':
            source_url = dep_dict["Furniture"][self.department][self.sub_department]
        else:
            source_url = dep_dict[self.department][self.sub_department]

        return source_url

    # The get_html has been modified to pass in a new parameter browsestoreoption.
    # Adding "browsestoreoption = 1" to the source url, we will only get the specific products from the selected stores.
    # While adding "browsestoreoption = 2" to the source url, we will get all the products from all the stores.
    def get_html(self, url, browsestoreoption):
        #ua = self.get_random_header()
        try:
            header = {'User-Agent':ua.random} 
        except:
            header={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)        AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'}
        payload = {'browsestoreoption': browsestoreoption}
#         cookies = {10022: dict(THD_PERSIST='C4%3D6177%2BManhattan%2059th%20Street%20-%20New%20York%2C%20NY%2B%3A%3BC4_EXP%3D1572030922%3A%3BC24%3D10022%3A%3BC24_EXP%3D1572030922%3A%3BC34%3D32.1%3A%3BC34_EXP%3D1540582116%3A%3BC39%3D1%3B8%3A00-20%3A00%3B2%3B7%3A00-22%3A00%3B3%3B7%3A00-22%3A00%3B4%3B7%3A00-22%3A00%3B5%3B7%3A00-22%3A00%3B6%3B7%3A00-22%3A00%3B7%3B7%3A00-22%3A00%3A%3BC39_EXP%3D1540498522'),
#               75209: dict(THD_PERSIST='C4%3D589%2BLemmon%20Ave%20-%20Dallas%2C%20TX%2B%3A%3BC4_EXP%3D1572032392%3A%3BC24%3D75209%3A%3BC24_EXP%3D1572032392%3A%3BC34%3D32.1%3A%3BC34_EXP%3D1540582829%3A%3BC39%3D1%3B8%3A00-20%3A00%3B2%3B6%3A00-22%3A00%3B3%3B6%3A00-22%3A00%3B4%3B6%3A00-22%3A00%3B5%3B6%3A00-22%3A00%3B6%3B6%3A00-22%3A00%3B7%3B6%3A00-22%3A00%3A%3BC39_EXP%3D1540499992')}
        #Pass in the random proxies from the proxy pool
        retry_count = 5
        while retry_count > 0:
            try:
                request= requests.get(url, proxies={'http':'http://'+ random.choice(gatherproxy_resp())},headers = header,
                     params=payload, cookies = self.cookies[self.location] )
                html = request.text
                soup = BeautifulSoup(html, 'lxml') #html.parser
                return soup
            except Exception:
                retry_count -= 1
        request= requests.get(url, headers = header, params=payload, cookies = self.cookies[self.location])
        html = request.text
        soup = BeautifulSoup(html, 'lxml')
        return soup
    
    #I built this get_load_more() method to click the "load more" button in some pages and get the whole page source.
    #Selenium will use the chrome driver to automate the click and wait procedure.
    #The max_result_num is collected from the web page with "load more" button:  
    #max_result_num = [int(i.text) for i in load_more_div.find_all('span')][-1]
    def get_load_more(self, url, max_result_num, browsestoreoption):
        driver = webdriver.Chrome('C:\\Users\\shbsc\\Downloads\\chromedriver_win32\\chromedriver.exe')  
        # Optional argument, if not specified will search path.
        url = url + "&browsestoreoption={}".format(browsestoreoption)
        driver.get(url)
        driver.add_cookie(cookie_dict=cookies[self.location])
        driver.get(url)

        for i in range(math.ceil(max_result_num//24)+1):
            try:
                python_button  = driver.find_element_by_class_name('js-load-more-btn')
                python_button.click()
                time.sleep(5)
                # time.sleep(5) # Let the user actually see something!
            except:
                break

        soup = BeautifulSoup(driver.page_source, 'lxml')
        driver.quit()
        return soup

    # The usage of this method is to get the brand dictionary (brand name: brand link). Notice that the stucture of-
    #- "Matresses" web page is different with others. So there will be different approach to get that information. 
    def get_brand_dict(self):
        url = self.get_source_url()
        soup = self.get_html(url, 2)
        if self.department == "Appliances":
            brand_list_raw = soup.find_all('ul', attrs = {'class': 'list list--type-plain u__text-align--left '})
            brand_name_ls = [i.text.strip().lower() for i in brand_list_raw[2].find_all('a')]
            brand_link_ls = ["https://www.homedepot.com" +  (re.search(r'href="(.*?)"',str(i)).group(1)) + '&Nao={}'
                              for i in brand_list_raw[2].find_all('a')]
            brand_dict = dict(zip(brand_name_ls, brand_link_ls))
        #elif self.department == "bedroom-furniture":
        else:
            brand_list_raw = soup.find_all('ul', attrs={"data-refinement": "Brand"})
            brand_name_ls = [i.text.replace("\n","").split("(")[0].lower() for i in brand_list_raw[0].find_all('li')]
            brand_link_ls = ["https://www.homedepot.com" + (re.search(r'href="(.*?)"',str(i)).group(1))  + '&Nao={}'
                              for i in brand_list_raw[0].find_all('a')]
            brand_dict = dict(zip(brand_name_ls, brand_link_ls))
        return brand_dict
    
    #This is the core code to crawl product information from a target web page. I collected current prices, prices saving,-
    #- brands, product descriptions and especially product links. So, for later analytic purpose, we can crawl more product -
    #- info through product links, such as reviews, ratings, etc. 
    def get_prod_info(self, soup):
        soup_p = soup.find('div', attrs={'id': "products"})
        prod_desc_raw = soup_p.find_all('a', attrs={'data-pod-type': "pr"})
        prod_url = ["https://www.homedepot.com" + (re.search(r'href="(.*?)"',str(i)).group(1)) for i in prod_desc_raw]
        prod_brand = [i.find('span', attrs={'class': 'pod-plp__brand-name'}).text for i in prod_desc_raw]
        prod_desc = [i.text.strip().split('\n')[-1] for i in prod_desc_raw]

        price_current_all = soup_p.find_all('div', attrs={'class': "price__numbers"})
        price_current_1 = [(i.text.strip()[:-2] + '.' + i.text.strip()[-2:]).strip("$") for i in price_current_all]
        price_current_2 = [float(i.replace(',','')) for i in price_current_1]

        price_savings_all = soup_p.find_all('div', attrs={'class': "info__savings"})
        price_savings = []
        for i in price_savings_all:
            try:
                price_savings.append(float(re.search(r'[0-9]+(\.[0-9]{2})', i.text.strip()).group()))
            except:
                price_savings.append(float(0.00))
        return price_current_2, price_savings, prod_brand, prod_desc, prod_url
    
    #Since the "Mattresses" page has different structure with other product pages, we should deal with them seperately.
    #The main problem here is how to crawl data from multiple pages. For non-mattresses pages like "Appliances", there -
    #- might be a bar below the page indicating the location like from page 1 to page 6. For page 2 of the search, the url-
    #- will add a parameter "Nao=24". For page 3 of the search, the parameter changes to "Nao=36". So we can just loop -
    #- through it to collect the information in each page.
    #On the other hand, for matreesses page, there can be a "load more" button below the product section if there're multiple-
    #- pages. Since this is a dynamic element, we have to use selenium to automate a series of click action to it.
    def run(self):
        if self.sub_department != 'Mattresses':
            price_current_ls = [];price_savings_ls=[];prod_brand_ls = [];prod_desc_ls = [];prod_url_ls = []
            brand_dict = self.get_brand_dict()
            if self.brand == "ge":
                url1 = brand_dict["ge appliances"]
            else:
                url1 = brand_dict[self.brand]
            url_current = url1.replace('&Nao={}','')
            soup = self.get_html(url_current, 1)
            #Crawling the page numbers from the bottom of the web page. If there is only one page, it will return an empty list.
            page_ls = list(filter(None, [int(i.text) if i.text!='' else i.text
                                         for i in soup.find_all('a', attrs={'class': 'hd-pagination__link'})]))
            try:
                price_current_2, price_savings, prod_brand, prod_desc, prod_url = self.get_prod_info(soup)
                price_current_ls.extend(price_current_2)
                price_savings_ls.extend(price_savings)
                prod_brand_ls.extend(prod_brand)
                prod_desc_ls.extend(prod_desc)
                prod_url_ls.extend(prod_url)
            except:
                df_dict = {"Department": [self.department], "Sub Department": [self.sub_department], "Current price": [0.00],
                          "Price saving": [0.00], "Brand":[ "No items on display"], "Description":[ "No items on display"], 
                           "Product link": ["No items on display"], "Location": [self.location]}
                result_df = pd.DataFrame(df_dict)
                return result_df
            # If there is only one page, we just store the result to a dataframe.
            if page_ls == []:
                Department_ls = [self.department]* len(price_current_ls)
                Sub_department_ls = [self.sub_department]* len(price_current_ls)
                location_ls = [self.location] * len(price_current_ls)
                df_dict = {"Department": Department_ls, "Sub Department": Sub_department_ls, "Current price":price_current_ls,
                          "Price saving": price_savings_ls, "Brand": prod_brand_ls, "Description": prod_desc_ls, "Product link":
                          prod_url_ls, "Location": location_ls}
                result_df = pd.DataFrame(df_dict)
            # If there are multiple pages, we need to loop through a list to pass in "Nao ={}" parameter to the url.
            else:
                ls = list(range(24, (max(page_ls)+2)*12,12)) 
                for i in ls:
                    try:
                        url_current = url1.format(i)
                        soup = self.get_html(url_current, 1)
                        price_current_2, price_savings, prod_brand, prod_desc, prod_url = self.get_prod_info(soup)
                        price_current_ls.extend(price_current_2)
                        price_savings_ls.extend(price_savings)
                        prod_brand_ls.extend(prod_brand)
                        prod_desc_ls.extend(prod_desc)
                        prod_url_ls.extend(prod_url)
                    except:
                        break
        # The structure is different for Mattresses page.
        elif self.sub_department == 'Mattresses':
            price_current_ls = [];price_savings_ls=[];prod_brand_ls = [];prod_desc_ls = [];prod_url_ls = []
            brand_dict = self.get_brand_dict()
            url1 = brand_dict[self.brand]
            url_current = url1.replace('&Nao={}','')
            soup = self.get_html(url_current, 1)
            #Find the "load more" button in the page.
            load_more_div = soup.find('div', attrs = {'id': 'load-more'})
            try:
                price_current_2, price_savings, prod_brand, prod_desc, prod_url = self.get_prod_info(soup)
                price_current_ls.extend(price_current_2)
                price_savings_ls.extend(price_savings)
                prod_brand_ls.extend(prod_brand)
                prod_desc_ls.extend(prod_desc)
                prod_url_ls.extend(prod_url)
            except:
                df_dict = {"Department": [self.department], "Sub Department": [self.sub_department], "Current price": [0.00],
                          "Price saving": [0.00], "Brand":[ "No items on display"], "Description":[ "No items on display"], 
                           "Product link": ["No items on display"], "Location": [self.location]}
                result_df = pd.DataFrame(df_dict)
                return result_df
            #If there is no "load more" button in the page, we can store the result directly to the result_df dataframe.
            if load_more_div == []:
                Department_ls = [self.department]* len(price_current_ls)
                Sub_department_ls = [self.sub_department]* len(price_current_ls)
                location_ls = [self.location] * len(price_current_ls)
                df_dict = {"Department": Department_ls, "Sub Department": Sub_department_ls, "Current price":price_current_ls,
                          "Price saving": price_savings_ls, "Brand": prod_brand_ls, "Description": prod_desc_ls, "Product link":
                          prod_url_ls, "Location": location_ls}
                result_df = pd.DataFrame(df_dict)
            #If there is a "load more" button, we can just call the get_load_more() method to get the source page.
            else:
                max_result_num = [int(i.text) for i in load_more_div.find_all('span')][-1]
                
                soup = get_load_more(self, url_current, max_result_num, 1)
                price_current_ls = [];price_savings_ls=[];prod_brand_ls = [];prod_desc_ls = [];prod_url_ls = []
                try:
                    price_current_2, price_savings, prod_brand, prod_desc, prod_url = self.get_prod_info(soup)
                    price_current_ls.extend(price_current_2)
                    price_savings_ls.extend(price_savings)
                    prod_brand_ls.extend(prod_brand)
                    prod_desc_ls.extend(prod_desc)
                    prod_url_ls.extend(prod_url)
                    
                except:
                    df_dict = {"Department": [self.department], "Sub Department": [self.sub_department], "Current price": [0.00],
                          "Price saving": [0.00], "Brand":[ "No items on display"], "Description":[ "No items on display"], 
                           "Product link": ["No items on display"], "Location": [self.location]}
                    result_df = pd.DataFrame(df_dict)
                    return result_df
                
                
        Department_ls = [self.department]* len(price_current_ls)
        Sub_department_ls = [self.sub_department]* len(price_current_ls)
        location_ls = [self.location] * len(price_current_ls)
        df_dict = {"Department": Department_ls, "Sub Department": Sub_department_ls, "Current price":price_current_ls,
                  "Price saving": price_savings_ls, "Brand": prod_brand_ls, "Description": prod_desc_ls, "Product link":
                  prod_url_ls, "Location": location_ls}
        result_df = pd.DataFrame(df_dict)
                
        
        return result_df



if __name__ == "__main__":
    
    try:
        # Import fake_useragent to create random useragent(i.e. fake headers)
        ua = UserAgent()
        # If You want to update saved database just:
        ua.update() 
    except FakeUserAgentError:
        pass

    #Create the search engine (dictionary) for department and sub_department first.
    d = homedepot_site_map()
    dep_dict = d.run()
    # [In]: dep_dict["Furniture"]["Bedroom Furniture"]["Mattresses"]
    # [Out]: 'https://www.homedepot.com/b/Furniture-Bedroom-Furniture-Mattresses/N-5yc1vZc7oe'
    
    #Create instances for specific department, sub_department, brands, and location.
    s1 = homedepot_crawler('Appliances', 'Dishwashers', 'LG',10022)
    s2 = homedepot_crawler('Appliances', 'Dishwashers', 'LG',75209)
    s3 = homedepot_crawler('Appliances', 'Dishwashers', 'Samsung',10022)
    s4 = homedepot_crawler('Appliances', 'Dishwashers', 'Samsung',75209)
    s5 = homedepot_crawler('Appliances', 'Refrigerators', 'Whirlpool',10022)
    s6 = homedepot_crawler('Appliances', 'Refrigerators', 'Whirlpool',75209)
    s7 = homedepot_crawler('Appliances', 'Refrigerators', 'GE',10022)
    s8 = homedepot_crawler('Appliances', 'Refrigerators', 'GE',75209)
    s9 = homedepot_crawler('Bedroom Furniture', 'Mattresses', 'Sealy',10022)
    s10 = homedepot_crawler('Bedroom Furniture', 'Mattresses', 'Sealy',75209)
    
    #Get the result dataframe by calling the run() method.
    result_1 = s1.run()
    result_2 = s2.run()
    result_3 = s3.run()
    result_4 = s4.run()
    result_5 = s5.run()
    result_6 = s6.run()
    result_7 = s7.run()
    result_8 = s8.run()
    result_9 = s9.run()
    result_10 = s10.run()
    
    #Concatenate the dataframes into one dataframe.
    result_df = pd.concat([result_1, result_2, result_3, result_4, result_5, result_6, result_7, result_8, result_9, result_10], 
                      axis =0, ignore_index= True)
    
    #Save the result to the working directory.
    result_df.to_csv("result_df.csv", index=False)

