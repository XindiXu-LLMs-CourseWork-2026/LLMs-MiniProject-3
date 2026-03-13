# LLMs-MiniProject-3

## Quick Start

1. Clone the repository

2. Install dependencies
```bash
 pip install -r requirements.txt
```

3. Set your OpenAI API key and Pinecone API Key as an environment variable
```bash
# Linux/macOS
export OPENAI_API_KEY="your_openai_api_key"
export ALPHAVANTAGE_API_KEY="your_alphavantage_api_key"

## check if the environment variables are set correctly
echo $OPENAI_API_KEY
echo ALPHAVANTAGE_API_KEY

# Windows
set OPENAI_API_KEY="your_openai_api_key"
set ALPHAVANTAGE_API_KEY="your_alphavantage_api_key"

## check if the environment variables are set correctly
echo $env:OPENAI_API_KEY
echo $env:ALPHAVANTAGE_API_KEY
```

4. Init database
```bash
python db/init_db.py
```

5. Run the Streamlit app
```bash
streamlit run app.py
```
Open your browser and navigate to http://localhost:8501 to access the app.
