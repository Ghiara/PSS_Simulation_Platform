mkdir -p ~/.streamlit/

echo "\
[general]\n\
email = \"yuan.meng@nio.io\"\n\
" > ~/.streamlit/credentials.toml

echo "\
[theme]\n\
base=\"dark\"\n\
primaryColor=\"#5efdef\"\n\
backgroundColor=\"#000000\"\n\
secondaryBackgroundColor=\"#2e2e35\"\n\
[server]\n\
headless = true\n\
enableCORS=false\n\
port = $PORT\n\
" > ~/.streamlit/config.toml