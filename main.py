import os
import datetime
import time
from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

# データモデル定義
class Site(db.Model):
  name = db.StringProperty(required=True)
  permalink = db.LinkProperty(required=True)
  date_on = db.DateTimeProperty(auto_now_add=True)

# データモデル定義
class Measuring(db.Model):
  measure = db.FloatProperty(required=True)
  date_on = db.DateTimeProperty(auto_now_add=True)
  name = db.ReferenceProperty(Site)

# インデックスページを表示します
CONTENT_TYPE = 'text/html; charset=utf-8'
INDEX_HTML = 'index.html'
class MainHandler(webapp.RequestHandler):
  def get(self):
    # サイト情報毎の計測情報を取得する
    measure_infos = []
    for site in Site.all():
      measureings = db.GqlQuery("SELECT * FROM Measuring WHERE name = :1 ORDER BY date_on DESC LIMIT 10", site)
      measure_infos.append({ 'name': site.name, 'url': site.permalink, 'measureings': measureings })

    # テンプレート情報
    path = os.path.join( os.path.dirname(__file__), INDEX_HTML )

    measureings = Measuring.all()

    # 出力
    self.response.headers['Content-Type'] = CONTENT_TYPE
    self.response.out.write( template.render(path, {'sites': measure_infos}) )

# サイト管理
SITE_LIST_HTML = 'site_list.html'
class SiteHandler(webapp.RequestHandler):
  # サイト一覧表示
  def get(self):
    path = os.path.join( os.path.dirname(__file__), SITE_LIST_HTML )
    self.response.headers['Content-Type'] = CONTENT_TYPE
    self.response.out.write( template.render(path, {'sites': Site.all()}) )

  # サイト登録
  def post(self):
    # パラメータ取得
    site_name = self.request.get('name')
    site_url  = self.request.get('url')

    # 入力が無ければサイト一覧へリダイレクトする
    if (not site_name or not site_url):
    	self.redirect('/site/')

    # サイトを登録します
    template_message = {'message': ''}
    try:
      site_obj = Site.get_or_insert( site_name, name=site_name, permalink=site_url)
    except:
      template_message['message'] = '[RegisterError] ' + site_name + ' : ' + site_url

    template_message['sites'] = Site.all()
    path = os.path.join( os.path.dirname(__file__), SITE_LIST_HTML )
    self.response.headers['Content-Type'] = CONTENT_TYPE
    self.response.out.write( template.render(path, template_message) )

# サイト情報を削除する
class SiteDeleteHandler(webapp.RequestHandler):
  def post(self):
    # 削除対象のサイトidsを取得する
    site_ids = self.request.get("site_id", allow_multiple=True)

    template_value = {'message': ''}
    for site_id in site_ids:
      # サイト情報を確認
      site = Site.get( site_id )
      if (not site):
        break

      # サイトの計測情報があれば削除する
      measureing = Measuring.all()
      measuring_of_site = measureing.filter('name =', site.name)
      if (0 != measuring_of_site.count()):
        db.delete( measuring_of_site )

      # サイト情報を削除する
      template_value['message'] = 'deleted : ' + site.name + '<br />'
      db.delete( site )

    # 出力
    template_values = { 'sites': Site.all() }
    path = os.path.join( os.path.dirname(__file__), SITE_LIST_HTML )
    self.response.headers['Content-Type'] = CONTENT_TYPE
    self.response.out.write( template.render(path, template_values) )

# レスポンスタイムを計測する
RESULT_HTML = 'result.html'
class FetchHandler(webapp.RequestHandler):
  def get(self):
    # 全てのサイト情報を取得する
    sites = Site.all()

    # サイト情報
    template_values = { 'message': '計測が完了しました' }
    if sites.count() == 0:
      # 出力
      template_values['message'] = '計測対象のサイトが登録されていません。'
    else:
      for site in sites:
        t = time.time()
        result = urlfetch.fetch( site.permalink )
        if result.status_code == 200:
          measuring = Measuring(measure = (time.time()-t),
                                name    = site )
          measuring.put()

    # 出力
    path = os.path.join( os.path.dirname(__file__), RESULT_HTML )
    self.response.headers['Content-Type'] = CONTENT_TYPE
    self.response.out.write( template.render(path, template_values) )

# webapp フレームワークのURLマッピングです
application = webapp.WSGIApplication(
                                     [
                                     	('/', MainHandler),
                                     	('/site/', SiteHandler),
                                     	('/site/delete/', SiteDeleteHandler),
                                     	('/site/fetch/', FetchHandler)
                                     ],
                                     debug=True)

# WebApp フレームワークのメインメソッドです
def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()