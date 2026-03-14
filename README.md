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
python -m db.init_db
```

5. mock Alpha Vantage Server
- Details can be found in [MOCK_ALPHA_VANTAGE_README.md](MOCK_ALPHA_VANTAGE_README.md)

6. Run the evaluator
```bash
# run calibration tests and sanity check
python -m evaluation.evaluation_tests
# run full evaluation and save the results into excel
python -m evaluation.full_evaluation_runner
```

7. Run the Streamlit app
```bash
streamlit run app.py
```
Open your browser and navigate to http://localhost:8501 to access the app.
