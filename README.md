# AI Video Generation Pipeline

## End-to-End AI Video Generation System

The **AI Video Generation System** is a modular machine learning pipeline that converts text scripts into fully rendered, downloadable videos using AI-powered speech synthesis, lip synchronization, and GPU-accelerated video rendering.

The system integrates multiple machine learning modules into a **single unified workflow**.

Text Script → Speech Audio → Lip Sync Processing → Video Rendering → Final MP4 Output

This repository contains the **backend application, ML pipeline modules, and orchestration logic** required to execute the system either via **API requests or direct pipeline execution**.

---

# System Objectives

The project is designed to achieve the following goals:

- Provide **one-click end-to-end video generation**
- Maintain **clear separation of ML modules**
- Support **scalable GPU-based video processing**
- Enable **job-based execution architecture**
- Ensure **clean folder structure and maintainability**
- Prepare a **backend-ready ML pipeline for API integration**
- Support **future cloud deployment and scaling**

---

# High-Level Architecture

The system follows a **modular pipeline architecture**.

User Input (Text + Avatar Selection)
│
▼
ML-1: Text-to-Speech & Voice Processing
│
▼
ML-2: Lip Sync & Face Processing
│
▼
ML-3: Video Rendering & Encoding
│
▼
Final Downloadable Video


Each module operates independently but follows a **strict input/output contract**.

---

# System Components

## Backend Layer

The backend handles request management, job orchestration, and pipeline triggering.

### Responsibilities

- Accept video generation requests
- Validate request inputs
- Create job workspace
- Trigger unified ML pipeline
- Track job status
- Return final video output

### Example API Endpoint

POST /generate-video


### Input Parameters

- text
- avatar selection
- voice configuration
- optional background settings

### Output

- Final MP4 file
- or downloadable file path

---

# ML Pipeline Modules

The ML pipeline contains three major modules.

---

## ML-1: Text-to-Speech & Voice Processing

ML-1 converts the input script into speech audio.

### Responsibilities

- Text preprocessing
- Language detection
- Multi-language TTS generation
- Voice cloning (future phase)
- Audio post-processing

### Input

Text Script


### Output

tts.wav
audio_metadata.json


The generated speech audio is passed directly to ML-2.

---

## ML-2: Lip Sync & Face Processing

ML-2 synchronizes avatar lip movements with the generated speech audio using the **Wav2Lip model**.

### Responsibilities

- Video normalization
- Frame extraction
- Face detection and alignment
- Mouth region extraction
- Mel spectrogram generation
- Audio-frame synchronization
- Wav2Lip inference
- Frame reconstruction
- Silent video generation

### Input

avatar_video.mp4
tts.wav


### Output

lipsynced_silent.mp4


This output video contains synchronized lip movement **without audio**.

---

## ML-3: Video Rendering & Encoding

ML-3 produces the final rendered video.

### Responsibilities

- Merge silent video with audio
- Perform GPU accelerated encoding
- Render final video
- Export production-ready MP4

### Input

lipsynced_silent.mp4
tts.wav


### Output

final_output.mp4


---

## 📂 Project Folder Structure

```

AI-VIDEO-GENERATION
│
├── backend
│   ├── core
│   │   ├── urls.py
│   │   └── wsgi.py
│   │
│   ├── video_app
│   │   ├── migrations
│   │   ├── services
│   │   ├── static
│   │   ├── templates
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   └── tests.py
│   │
│   ├── manage.py
│   └── db.sqlite3
│
├── ml_pipeline
│   ├── ml1_tts
│   ├── ml2_lipsync
│   ├── ml3_render
<<<<<<< HEAD
│   ├── init.py
=======
│   ├── **init**.py
>>>>>>> 4a734e2cabf15dfa449aadc6c0151c59c32369b8
│   └── run_pipeline.py
│
├── env
├── .gitignore
└── README.md

```



### Folder Design Principles

- Separation between backend and ML pipeline
- Modular ML components
- Pipeline orchestration control
- Maintainable development environment

---

# Job-Based Processing Architecture

Each video generation request creates an isolated job workspace.

jobs/{job_id}/
input/
ml1/
ml2/
ml3/
logs/
status.json


### Advantages

- Job isolation
- Parallel execution
- Debug-friendly logs
- Easy cleanup after completion

---

# Pipeline Execution

The system supports two execution modes.

---

## Direct Pipeline Execution

Run the pipeline manually.


python ml_pipeline/run_pipeline.py


This will:

1. Generate speech from text
2. Perform lip synchronization
3. Render the final video

---

## API Execution

Trigger pipeline through backend API.

POST /generate-video


**Backend workflow:**

Validate Request
↓
Create Job Workspace
↓
Trigger ML Pipeline
↓
Monitor Execution
↓
Return Final Video


---

# Logging & Monitoring

Each module logs the following information:

- Stage execution time
- Total processing time
- Frame count
- Audio duration
- GPU utilization
- Error messages

**Logs are stored in:**

logs/
jobs/{job_id}/logs/


---

# Error Handling Strategy

The system follows **fail-fast architecture**.

If any stage fails:

- Pipeline execution stops
- Error is logged
- Downstream modules are not executed
- Job status is updated

This prevents corrupted outputs from propagating through the pipeline.

---

# Scalability Considerations

The architecture supports future scaling.

**Planned improvements include:**

- GPU worker pools
- Distributed job queues (Celery + Redis)
- AWS GPU infrastructure
- S3 based video storage
- Horizontal scaling
- Microservice architecture

---

# Technology Stack

## Backend

- Python
- Django

## Machine Learning

- PyTorch
- TensorFlow
- Wav2Lip
- Multi-language TTS

## Video Processing

- FFmpeg
- GPU Encoding (NVENC)

## Storage

- AWS S3 (future integration)

## Database

- PostgreSQL (planned)
- SQLite (development)

---

# Design Principles

The system follows key engineering principles:

- Modular architecture
- Strict input-output contracts
- Clear module boundaries
- Job-level isolation
- GPU optimized processing
- Clean pipeline orchestration

---

# End-to-End Workflow

User Script
↓
ML-1: Generate Speech Audio
↓
ML-2: Lip Synchronization
↓
ML-3: Video Rendering
↓
Final MP4 Video


The entire system operates as a **unified AI video generation pipeline** while maintaining **modular independence between components**.

---
