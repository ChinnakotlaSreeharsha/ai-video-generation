from ml_pipeline.run_pipeline import run_pipeline

def generate_video(text, avatar):
    return run_pipeline(text=text, avatar_id=avatar)