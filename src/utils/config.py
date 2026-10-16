class Config:
    SUPPORTED_PLATFORMS = ['facebook', 'instagram', 'twitter', 'youtube', 'tiktok']
    MAX_FILE_SIZE = 110  # KB
    SUPPORTED_FORMATS = ['.txt', '.csv', '.xlsx', '.xls']
    
    PAGE_CONFIG = {
        "page_title": "Analizador Crítico del Discurso",
        "page_icon": "📊", 
        "layout": "wide"
    }
    
    ANALYSIS_SETTINGS = {
        'min_word_length': 3,
        'similarity_threshold': 0.75,
        'top_words_limit': 50
    }