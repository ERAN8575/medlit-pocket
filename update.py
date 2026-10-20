#!/usr/bin/env python3
"""Fetch PubMed, summarize abstract with optional OpenAI, publish JSON, Telegram digest."""
import os,json,time,re,html,logging,datetime,xml.etree.ElementTree as ET
from pathlib import Path
import requests
ROOT=Path(__file__).parent; DB=ROOT/'data'/'articles.json'; API='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
TOPICS={
'military':'("military medicine"[tiab] OR "combat casualty"[tiab] OR "military medical"[tiab] OR "operational medicine"[tiab]) AND (education[tiab] OR training[tiab] OR simulation[tiab] OR qualitative[tiab] OR reflection[tiab])',
'qual':'("medical education"[tiab] OR "health professions education"[tiab]) AND ("thematic analysis"[tiab] OR "qualitative research"[tiab] OR "grounded theory"[tiab] OR "reflexive thematic"[tiab])',
'sim':'(simulation[tiab] OR experiential learning[tiab]) AND (military[tiab] OR medical students[tiab]) AND (qualitative[tiab] OR debriefing[tiab] OR feedback[tiab])',
}
PRIORITY={'medical education','academic medicine','medical teacher','advances in health sciences education','simulation in healthcare','military medicine','aem education and training'}
SEED=['37226060','37226055','34585038','33206966','40402561','41192983','37201487','37226058','36656762','40621288','40178910']
S=requests.Session();S.headers.update({'User-Agent':'MedLitPocket/2.0 (academic research; contact via NCBI_EMAIL)'})
logging.basicConfig(level=logging.INFO,format='%(levelname)s %(message)s')
def request(endpoint,params):
 p=dict(params);p.update({'tool':'medlit_pocket'});
 if os.getenv('NCBI_EMAIL'):p['email']=os.environ['NCBI_EMAIL']
 for attempt in range(4):
  try:
   r=S.get(API+endpoint,params=p,timeout=35);r.raise_for_status();time.sleep(.4);return r
  except requests.RequestException:
   if attempt==3:raise
   time.sleep(2**attempt)
def txt(node):return ''.join(node.itertext()).strip() if node is not None else ''
def ids(query,days,limit):
 j=request('esearch.fcgi',{'db':'pubmed','term':query,'retmode':'json','retmax':limit,'datetype':'edat','reldate':days,'sort':'date'}).json()
 return j['esearchresult']['idlist']
def fetch_articles(pmids):
 if not pmids:return []
 root=ET.fromstring(request('efetch.fcgi',{'db':'pubmed','id':','.join(pmids),'retmode':'xml'}).content)
 out=[]
 for item in root.findall('./PubmedArticle'):
  med=item.find('./MedlineCitation'); art=med.find('./Article') if med is not None else None
  if art is None:continue
  pmid=txt(med.find('./PMID')); title=txt(art.find('./ArticleTitle')); journal=txt(art.find('./Journal/Title'))
  sections=[]
  for n in art.findall('./Abstract/AbstractText'):
   label=n.get('Label') or n.get('NlmCategory') or ''; value=txt(n)
   if value:sections.append((label+': ' if label else '')+value)
  abstract='\n'.join(sections);doi=''
  for node in item.findall('./PubmedData/ArticleIdList/ArticleId'):
   if node.get('IdType')=='doi':doi=txt(node)
  pub=art.find('./Journal/JournalIssue/PubDate'); year=txt(pub.find('./Year')) if pub is not None else ''
  if not year:
   match=re.search(r'\b(?:19|20)\d{2}\b',txt(pub));year=match.group(0) if match else ''
  out.append({'id':pmid,'title':title,'journal':journal,'year':year,'doi':doi,'abstract':abstract,'url':f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/','source':'PubMed abstract','updated':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 return out
def fallback(a):
 return {'quick':('【研究背景與問題】\n'+a['title']+'\n\n【原始摘要（英文，尚未完成AI分析）】\n'+(a['abstract'] or 'PubMed未提供摘要。')),'deep':('【研究資料】\n'+a['journal']+' ('+str(a['year'])+')；PMID '+a['id']+'\n\n【摘要原文】\n'+(a['abstract'] or 'PubMed未提供摘要。')+'\n\n【評讀提示】\n請核對全文的研究取樣、資料蒐集、分析方法、反身性、可信度與研究限制；本頁未推論摘要未提供的結果。'),'ai_status':'pending'}
def analyze(a,client):
 if not client or not a['abstract']:return fallback(a)
 instruction='''你是醫學教育質性研究方法專家。只根據提供的 PubMed 標題與摘要，用繁體中文產出 JSON 物件，恰好含 quick、deep 兩個字串。quick 目標500–800中文字；deep目標1500–2200中文字，但資料不足時寧可短，不可灌水或編造。quick分段：研究背景、研究問題、設計/樣本、重要結果（只列摘要實際記載的數據/主題）、為何值得讀。deep分段：研究脈絡、研究問題、研究設計與樣本、資料蒐集與分析、核心結果逐項解讀、研究限制（明示/推論分開）、方法學評讀、軍陣醫學教學/學生反思資料的應用、下一步閱讀全文的查核清單。若文章是方法指引則調整結構。任何摘要沒說的細節明確標記「摘要未交代，需查全文」。不得捏造引言、訪談逐字稿、數值、效應量或作者主張。研究者建議需標示「延伸建議」。請不要稱已閱讀全文。'''
 response=client.chat.completions.create(model=os.getenv('OPENAI_MODEL','gpt-4.1-mini'),response_format={'type':'json_object'},messages=[{'role':'system','content':instruction},{'role':'user','content':json.dumps({'title':a['title'],'journal':a['journal'],'abstract':a['abstract']},ensure_ascii=False)}],temperature=0.1,timeout=90)
 data=json.loads(response.choices[0].message.content)
 if not isinstance(data.get('quick'),str) or not isinstance(data.get('deep'),str):raise ValueError('AI JSON missing fields')
 return {'quick':data['quick'],'deep':data['deep'],'ai_status':'abstract_only'}
def send_telegram(new):
 token=os.getenv('TELEGRAM_BOT_TOKEN');chat=os.getenv('TELEGRAM_CHAT_ID');url=os.getenv('SITE_URL','https://eran8575.github.io/medlit-pocket/')
 if not token or not chat or not new:return
 lines=['📚 MedLit Pocket｜今日新增文獻 '+str(len(new))+' 篇','']
 for i,a in enumerate(new[:5],1):lines.append(f"{i}. {a['title'][:110]}\n{a['journal']} · {a['year']}\n{a['url']}\n")
 lines.append('📖 手機閱讀：'+url)
 r=S.post('https://api.telegram.org/bot'+token+'/sendMessage',json={'chat_id':chat,'text':'\n'.join(lines)[:3900],'disable_web_page_preview':True},timeout=25);r.raise_for_status()
def main():
 old=json.loads(DB.read_text(encoding='utf-8')) if DB.exists() else {'articles':[]}
 articles={a['id']:a for a in old.get('articles',[])}; days=int(os.getenv('DAYS_BACK','14')); per=int(os.getenv('PER_TOPIC','12'))
 candidate=set(SEED if not articles else [])
 for topic,query in TOPICS.items():
  try:candidate.update(ids(query,days,per))
  except Exception as e:logging.warning('Topic %s: %s',topic,e)
 missing=sorted(candidate-set(articles));logging.info('New PMIDs: %d',len(missing))
 fresh=[]
 for i in range(0,len(missing),30):
  try:fresh.extend(fetch_articles(missing[i:i+30]))
  except Exception as e:logging.warning('Fetch failed: %s',e)
 client=None
 if os.getenv('OPENAI_API_KEY'):
  from openai import OpenAI
  client=OpenAI(api_key=os.environ['OPENAI_API_KEY'],max_retries=2)
 # process only limited number of new records each day to cap API spending
 fresh.sort(key=lambda a:(a['journal'].lower() in PRIORITY, bool(a['abstract'])),reverse=True)
 ai_limit=int(os.getenv('MAX_AI_ARTICLES','8'))
 for i,a in enumerate(fresh):
  try:a.update(analyze(a,client if i<ai_limit else None))
  except Exception as e:logging.warning('AI %s: %s',a['id'],e);a.update(fallback(a))
  a['tags']=[t for t in TOPICS if any(w in (a['title']+' '+a['abstract']).lower() for w in {'military':['military','combat','operational medicine'],'qual':['qualitative','thematic','grounded theory','phenomenolog'],'sim':['simulation','simulated','experiential','debriefing']}[t])]
  if not a['tags']:a['tags']=['qual']
  a['priority']=a['journal'].lower() in PRIORITY
  articles[a['id']]=a
 # upgrade pending articles gradually if API key is configured
 if client:
  pending=[a for a in articles.values() if a.get('ai_status')=='pending' and a.get('abstract')]
  for a in pending[:int(os.getenv('MAX_BACKFILL_AI','3'))]:
   try:a.update(analyze(a,client))
   except Exception as e:logging.warning('Backfill %s: %s',a['id'],e)
 output={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'articles':sorted(articles.values(),key=lambda a:(a.get('updated',''),a['id']),reverse=True)[:300]}
 DB.parent.mkdir(exist_ok=True);DB.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
 logging.info('Saved %d articles',len(output['articles']))
 try:send_telegram(fresh)
 except Exception as e:logging.warning('Telegram failed: %s',e)
if __name__=='__main__':main()
