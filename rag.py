"""RAG: локальный TF-IDF поиск + опциональная реальная LLM."""
import os,re
import httpx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def build_index(articles):
    vectorizer=TfidfVectorizer(analyzer="char",ngram_range=(2,4))
    matrix=vectorizer.fit_transform([a["title"]+" "+a["content"] for a in articles])
    return vectorizer,matrix

def retrieve(query,articles,vectorizer,matrix,k=3):
    if not query.strip(): raise ValueError("Пустой вопрос")
    similarities=cosine_similarity(vectorizer.transform([query]),matrix)[0]
    order=sorted(range(len(articles)),key=lambda i:float(similarities[i]),reverse=True)[:max(1,min(k,len(articles)))]
    return [{**articles[i],"score":round(float(similarities[i]),4)} for i in order if float(similarities[i])>0]

def generate(query,sources):
    if not sources:
        return {"answer":"В базе знаний нет подходящих материалов. Создайте заявку специалисту.","answer_source":"template","llm_model":None,"llm_error":None,"cited_ids":[],"unknown_cited_ids":[]}
    fallback="По материалам базы знаний: "+" ".join("["+s["id"]+"] "+s["content"] for s in sources[:2])
    key=os.getenv("LLM_API_KEY","").strip()
    if not key:
        return {"answer":fallback,"answer_source":"template","llm_model":None,"llm_error":None,"cited_ids":[],"unknown_cited_ids":[]}
    model=os.getenv("LLM_MODEL","nemotron-3-nano:4b")
    url=os.getenv("LLM_API_URL","http://localhost:11434/v1/chat/completions")
    context="\n".join("["+s["id"]+"] "+s["title"]+": "+s["content"] for s in sources)
    prompt=("Ответь по-русски, только по приведённым источникам. В конце каждого утверждения ставь [id] источника. "
            "Если данных недостаточно, скажи об этом.\nИсточники:\n"+context+"\nВопрос: "+query)
    try:
        r=httpx.post(url,headers={"Authorization":"Bearer "+key},json={"model":model,"messages":[{"role":"user","content":prompt}],"temperature":0.3,"max_tokens":500},timeout=45)
        r.raise_for_status()
        answer=r.json()["choices"][0]["message"]["content"]
        if not isinstance(answer,str) or not answer.strip():raise ValueError("Пустой ответ модели")
        mentioned=re.findall(r"\[([a-zA-Z0-9_-]+)\]",answer)
        allowed={s["id"] for s in sources}
        return {"answer":answer,"answer_source":"llm","llm_model":model,"llm_error":None,"cited_ids":sorted(set(mentioned)&allowed),"unknown_cited_ids":sorted(set(mentioned)-allowed)}
    except Exception as e:
        # Не выводим ключ, URL или содержимое заголовков авторизации
        return {"answer":fallback,"answer_source":"template","llm_model":None,"llm_error":type(e).__name__,"cited_ids":[],"unknown_cited_ids":[]}
