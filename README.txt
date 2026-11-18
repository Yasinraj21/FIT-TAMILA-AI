FIT Tamila AI — starter project

Windows setup:
1. Extract the ZIP.
2. Open Command Prompt and cd into the fit_tamila_ai folder.
3. Run: python -m pip install -r requirements.txt
4. Run: python -m streamlit run app.py

This is a bilingual, multi-user, offline-first prototype with profile storage, BMI/BMR/TDEE estimates, Tamil food logging, workout templates, progress tracking, and charts.

Important: Since no API key was selected, the coach is a rule-based offline helper, not a live LLM. Next step: connect a pretrained LLM and build RAG over a curated food/recipe/exercise knowledge base. Food values are illustrative estimates, not medical advice. Local account security is prototype-level, not production-ready.
