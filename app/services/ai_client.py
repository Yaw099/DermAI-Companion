import os
import requests
from openai import OpenAI
import xml.etree.ElementTree as ET

def search_pubmed(query, max_results=5):
    """
    Search PubMed for medical articles and return detailed results with abstracts
    Args:
        query: Search query string
        max_results: Maximum number of articles to return
    Returns:
        Dictionary with formatted results and article data, or None if no results
    """
    try:
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        
        #Search for article IDs
        search_url = f"{base_url}esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": f"{query} AND dermatology[MeSH Terms]",
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance"
        }
        
        print(f"🔍 Searching PubMed for: {query}")
        search_response = requests.get(search_url, params=search_params, timeout=10)
        search_data = search_response.json()
        
        if "esearchresult" not in search_data or "idlist" not in search_data["esearchresult"]:
            print("No search results found")
            return None
        
        ids = search_data["esearchresult"]["idlist"]
        
        if not ids:
            print("No article IDs returned")
            return None
        
        print(f"Found {len(ids)} articles")
        
        #Get article summaries
        summary_url = f"{base_url}esummary.fcgi"
        summary_params = {
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "json"
        }
        
        summary_response = requests.get(summary_url, params=summary_params, timeout=10)
        summary_data = summary_response.json()
        
        #Get full abstracts
        fetch_url = f"{base_url}efetch.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "xml",
            "rettype": "abstract"
        }
        
        print("📄 Fetching article abstracts...")
        fetch_response = requests.get(fetch_url, params=fetch_params, timeout=15)
        
        #Parse XML to extract abstracts
        abstracts = {}
        try:
            root = ET.fromstring(fetch_response.content)
            for article in root.findall('.//PubmedArticle'):
                pmid_elem = article.find('.//PMID')
                abstract_elem = article.find('.//Abstract/AbstractText')
                
                if pmid_elem is not None and abstract_elem is not None:
                    pmid = pmid_elem.text
                    abstract = abstract_elem.text or "No abstract available"
                    abstracts[pmid] = abstract
        except ET.ParseError as e:
            print(f"Warning: Could not parse abstracts: {e}")
        
        #Formatting results 
        articles = []
        formatted_text = "PUBMED RESEARCH ARTICLES\n\n"
        
        for i, article_id in enumerate(ids, 1):
            if article_id not in summary_data["result"]:
                continue
                
            article = summary_data["result"][article_id]
            
            #Get article info
            title = article.get("title", "No title available")
            authors = article.get("authors", [])
            author_names = ", ".join([a.get("name", "") for a in authors[:3]])
            if len(authors) > 3:
                author_names += " et al."
            
            source = article.get("source", "Unknown journal")
            pub_date = article.get("pubdate", "Unknown date")
            abstract = abstracts.get(article_id, "Abstract not available")
            
            #Store the article data
            article_data = {
                "pmid": article_id,
                "title": title,
                "authors": author_names,
                "journal": source,
                "date": pub_date,
                "abstract": abstract,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{article_id}/"
            }
            articles.append(article_data)
            
            #Format for AI context
            formatted_text += f"[SOURCE {i}]\n"
            formatted_text += f"PMID: {article_id}\n"
            formatted_text += f"Title: {title}\n"
            formatted_text += f"Authors: {author_names}\n"
            formatted_text += f"Journal: {source} ({pub_date})\n"
            formatted_text += f"Abstract: {abstract}\n"
            formatted_text += f"URL: https://pubmed.ncbi.nlm.nih.gov/{article_id}/\n"
            formatted_text += "\n" + "="*60 + "\n\n"
        
        formatted_text += "End of Research Articles\n"
        
        print(f"Successfully fetched {len(articles)} articles with abstracts")
        
        return {
            "formatted_text": formatted_text,
            "articles": articles,
            "count": len(articles)
        }
    
    except requests.Timeout:
        print("PubMed API timeout")
        return None
    except requests.RequestException as e:
        print(f"PubMed API error: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error in PubMed search: {str(e)}")
        return None


def ask_ai(conversation):
    """
    Process user query with PubMed RAG and return AI response with citations
    Args:
        conversation: List of message dicts with 'role' and 'content' 
    Returns:
        String response from AI with citations
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "(Demo) AI is not configured properly. Add your OpenAI API key to environment variables."
    
    try:
        client = OpenAI(api_key=api_key)
        
        #Validate conversation input
        if not conversation or len(conversation) == 0:
            return "Please ask a question about dermatology."
        
        #Get the latest user question
        user_question = conversation[-1].get("content", "")
        if not user_question.strip():
            return "Please provide a valid question."
        

        print(f"USER QUESTION: {user_question}")
        
        #Search PubMed for relevant research
        pubmed_results = search_pubmed(user_question, max_results=5)
        
        if pubmed_results and pubmed_results["count"] > 0:
            #Build system prompt with strict instructions
            system_message = {
                "role": "system",
                "content": """You are a dermatology educational assistant that provides information EXCLUSIVELY from peer-reviewed medical literature.

                Rules:
                1. Base your answer ONLY on the PubMed research articles provided below
                2. You MUST cite every claim using the format: [Source X, PMID: XXXXXXXX]
                3. NEVER use your general knowledge - only use the provided research
                4. If the research doesn't answer the question, say: "I couldn't find specific information about this in the current medical literature."
                5. Always include this disclaimer at the end: "Note: This information is for educational purposes only. Please consult a dermatologist for proper diagnosis and treatment."

                Citation Requirements:
                - After EVERY factual statement, add [Source X, PMID: XXXXXXXX]
                - Example: "Eczema is caused by genetic factors [Source 1, PMID: 12345678] and environmental triggers [Source 2, PMID: 87654321]."
                - Use multiple sources when they support the same point
                - At the end, provide a "Sources" section listing all PMIDs with titles

                Be clear, accurate, and helpful while maintaining strict citation standards."""
            }
            
            #Add the research context and user question
            context_message = {
                "role": "user",
                "content": f"{pubmed_results['formatted_text']}\n\nUSER QUESTION\n{user_question}\n\nRemember: Cite every claim with [Source X, PMID: XXXXXXXX] format."
            }
            
            #Build messages with conversation history
            messages = [system_message]
            
            #Add previous conversation (excluding last message since we're reformatting it)
            if len(conversation) > 1:
                for msg in conversation[:-1]:
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            
            #Add current question with PubMed context
            messages.append(context_message)
            
        else:
            #If No PubMed results found, then this occurs
            print("No PubMed results - informing user")
            return ("I apologize, but I couldn't find peer-reviewed research articles on this topic in PubMed. "
                   "This could mean:\n"
                   "1. The topic might be too specific or niche\n"
                   "2. Different search terms might yield better results\n"
                   "3. This may not be a dermatology-related question\n\n"
                   "Please try rephrasing your question or consult a dermatologist for personalized advice.")
        
        #Call OpenAI API
        print("Calling OpenAI API...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=1500,
            temperature=0.3  #Lower temperature for factual accuracy
        )
        
        ai_response = response.choices[0].message.content
        print("AI response generated with citations\n")
        
        return ai_response
    
    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        print(f"{error_msg}")
        return error_msg