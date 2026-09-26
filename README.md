# magic-clone-local

Local Gradio app that generates a 3-scene storyboard and exports a real MP4 slideshow under `outputs/`.

> This is a **storyboard slideshow video** (still images turned into MP4), not full motion animation.

## What it does

1. Uses a Hugging Face chat model to write a 3-scene storyboard.
2. Uses a Hugging Face image model to generate one image per scene.
3. Renders those images into an MP4 locally.
4. Shows the MP4 in Gradio and saves files in `outputs/`.

## Windows setup (beginner-friendly)

### 1) Install Python

- Download Python 3.10+ from: https://www.python.org/downloads/windows/
- During install, enable **Add Python to PATH**.

### 2) Download or open this project folder

Make sure these files are present:
- `magic_clone.py`
- `requirements.txt`
- `Start_Magic_Clone.bat`

### 3) Set your Hugging Face token safely (recommended)

In **PowerShell**:

```powershell
setx HF_TOKEN "hf_your_token_here"
```

Then close and reopen PowerShell/Command Prompt so the variable is available.

> Do **not** hard-code your token in source files.

To create a token: https://huggingface.co/settings/tokens

### 4) Launch the app

Double-click:

- `Start_Magic_Clone.bat`

The launcher installs dependencies and starts Gradio.

### 5) Use the app

- Enter a prompt and style.
- Click **Generate storyboard + MP4**.
- Wait for scene images and MP4 generation.
- Download/use the video from the Gradio video output.

## Output files

Generated files are saved in:

- `outputs/YYYYMMDD_HHMMSS_ffffff_scene_1.png`
- `outputs/YYYYMMDD_HHMMSS_ffffff_scene_2.png`
- `outputs/YYYYMMDD_HHMMSS_ffffff_scene_3.png`
- `outputs/YYYYMMDD_HHMMSS_ffffff.mp4`

## Model/access caveats

- Default text model: `meta-llama/Llama-3.1-8B-Instruct`
- Default image model: `stabilityai/stable-diffusion-xl-base-1.0`

If your account cannot access a model, change the model name in **Advanced settings**.
The app now reports clear actionable errors when storyboard/image generation fails.

## Troubleshooting

- **"HF_TOKEN is not set"**: set it with `setx HF_TOKEN "hf_..."`, restart terminal, relaunch.
- **Image generation failed**: verify token permissions and model availability on Hugging Face.
- **No MP4 generated**: check status output; if image generation fails first, no video is created.
- **Install issues**: run manually in project folder:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python magic_clone.py
```
