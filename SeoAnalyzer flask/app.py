from flask import Flask, request , render_template
from bs4 import BeautifulSoup
import requests
import time
import socket
from urllib.parse import urlsplit
import nltk
import pandas as pd

app = Flask(__name__)

@app.route('/home')
def home():
    return render_template("index.html")

def keyword_consistency(soup):
    keywords = []
    title = soup.title.text
    keywords.extend(title.split())
    desc = soup.find("meta",  property="og:description")
    if desc:
        desc = desc["content"]
        keywords.extend(desc.split())
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    for heading in headings:
        keywords.extend(heading.text.split())
    keywords = nltk.FreqDist(keywords)
    keywords_df = pd.DataFrame(keywords.items(),columns=['Keywords','Freq'])
    keywords_df["Title"] = title
    keywords_df["Desc"] = desc if desc else ""
    keywords_df["<H>"] = ", ".join([heading.name for heading in headings])
    return keywords_df

@app.route('/')
def index():
    return '''
        <form method="POST" action="/report">
            URL: <input type="text" name="url"><br>
            <input type="submit" value="Generate Report">
        </form>
    '''

@app.route('/report', methods=['POST'])
def report():
    url = request.form['url']
    if not url:
        return "Please enter a URL"
    if not url.startswith(("http", "https")):
        return "Please enter a valid URL"
    try:
        start = time.time()
        page = requests.get(url)
        end = time.time()
        soup = BeautifulSoup(page.content, 'html.parser')
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        headings_list = []
        for heading in headings:
            headings_list.append("{}:{}".format(heading.name,heading.text))
        links = soup.find_all('a')
        pages = [link["href"] for link in links if "href" in link.attrs and (link["href"].endswith(".html") or link["href"].endswith(".htm"))]
        speed = end - start
        domain_name = "{.netloc}".format(urlsplit(url))
        server_ip = socket.gethostbyname(domain_name)
        ip_canonicalization = requests.get('http://'+server_ip)
        keywords_df = keyword_consistency(soup)
        img_tags = soup.find_all('img')
        alt_attributes2 = [img['alt'] for img in img_tags if 'alt' in img.attrs]
        img_tags = soup.find_all('img')
        alt_attributes = {}
        missing_alt_attributes = []
        meta_tags = soup.find_all('meta')
        meta_keywords = ''
        for tag in meta_tags:
            if 'name' in tag.attrs and tag['name'].lower() == 'keywords':
                meta_keywords = tag.get('content', 'No Meta Keywords Found')
                break

        print(meta_keywords)
        print(soup.prettify())
        for tag in meta_tags:
            print(tag)
        print("meta_keywords: {}".format(meta_keywords))
        sitemap_url = url + '/sitemap.xml'
        sitemap_response = requests.get(sitemap_url)
        if sitemap_response.status_code == 200:
            sitemap_status = 'Present'
        elif sitemap_response.status_code == 404:
            sitemap_status = 'Not Found'
        else:
            sitemap_status = 'Not Present'
        robots_url = url + '/robots.txt'
        robots_response = requests.get(robots_url)
        if robots_response.status_code == 200:
            robots_status = 'Present'
        else:
            robots_status = 'Not Present'
        return '''
        <h1>Report</h1>
        <p>Number of headings: {}</p>
        <p>Number of links: {}</p>
        <p>Number of pages: {}</p>
        <p>Speed: {} seconds</p>
        <p>Server IP: {}</p>
        <p>IP Canonicalization: {}</p>
        <h2>Headings</h2>
        {}
        <p>No of Headings: {}</p>
        <h2>Keyword Consistency</h2>
        {}
        <h2>Alt Attributes</h2>
        {}
        <h2>Missing Alt Attributes</h2>
        <p>Number of missing alt attributes: {}</p>
        {}
        <h2>Meta Keywords</h2>
        <p>{}</p>
        <h2>XML Sitemap</h2>
        <p>{}</p>
        <h2>Robots.txt</h2>
        <p>{}</p> 
        '''.format(len(headings), len(links), len(pages), speed, server_ip, ip_canonicalization.url, headings_list, len(headings_list) , keywords_df.to_html(),alt_attributes, len(missing_alt_attributes), missing_alt_attributes, meta_keywords,sitemap_status,robots_status)

    except Exception as e:
        return "An error occurred: {}".format(e)

    if __name__ == '__main__':
        nltk.download('punkt')
        app.run(debug=True)

