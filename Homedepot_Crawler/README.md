# Homedepot Scrapper

Provides a web scraping tool for [www.homedepot.com](https://www.homedepot.com), including a search engine and a crawler.

- The *homedepot_site_map* class grab the hierarchical department structure from site-map by generating a nested dictionary.

- The *homedepot_crawler* class is built to scrape product information from sepecific department, sub_department, brand 
and location and store the result to a dataframe.
