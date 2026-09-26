import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import gradio as gr
import imageio_ffmpeg
from huggingface_hub import InferenceClient

OUTPUTS_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

DEFAULT_TEXT_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
DEFAULT_IMAGE_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"


class SceneImageGenerationError(RuntimeError):
    def __init__(self, message: str, image_paths: List[Path]):
        super().__init__(message)
        self.image_paths = image_paths


def _create_client() -> Tuple[InferenceClient, str]:
    token = os.getenv("HF_TOKEN", "").strip()
    return InferenceClient(token=token or None), token


def _chat_completion(client: InferenceClient, model: str, messages: List[dict]) -> str:
    if hasattr(client, "chat") and hasattr(client.chat, "completions"):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=350,
            temperature=0.8,
        )
        content = response.choices[0].message.content
        return (content or "").strip() if isinstance(content, str) else str(content)

    # Compatibility path for older huggingface_hub versions.
    response = client.chat_completion(
        model=model,
        messages=messages,
        max_tokens=350,
        temperature=0.8,
    )
    content = response.choices[0].message.content
    return (content or "").strip() if isinstance(content, str) else str(content)


def _parse_storyboard(storyboard_text: str) -> List[str]:
    scenes: List[str] = []
    for raw_line in storyboard_text.splitlines():
        line = raw_line.strip().strip("-*")
        if not line:
            continue
        if line.lower().startswith("scene"):
            parts = line.split(":", 1)
            scene_text = parts[1].strip() if len(parts) > 1 else line
            if scene_text:
                scenes.append(scene_text)
        else:
            scenes.append(line)
        if len(scenes) >= 3:
            break

    if len(scenes) < 3:
        fallback = [part.strip() for part in storyboard_text.replace("\n", " ").split(".") if part.strip()]
        for item in fallback:
            if len(scenes) >= 3:
                break
            scenes.append(item)

    while len(scenes) < 3:
        scenes.append("A cinematic continuation of the story with consistent style.")

    return scenes[:3]


def generate_storyboard(client: InferenceClient, prompt: str, style: str, text_model: str) -> Tuple[str, List[str]]:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a storyboard writer. Return exactly three short lines, each starting with "
                "'Scene 1:', 'Scene 2:', and 'Scene 3:'. Keep it visual and concise."
            ),
        },
        {
            "role": "user",
            "content": f"Prompt: {prompt}\nStyle: {style}",
        },
    ]

    storyboard_text = _chat_completion(client, text_model, messages)
    if not storyboard_text:
        raise RuntimeError("Storyboard generation returned an empty response.")

    scenes = _parse_storyboard(storyboard_text)
    formatted_storyboard = "\n".join([f"Scene {i + 1}: {scene}" for i, scene in enumerate(scenes)])
    return formatted_storyboard, scenes


def generate_scene_images(
    client: InferenceClient,
    scenes: List[str],
    style: str,
    image_model: str,
    run_stamp: str,
) -> List[Path]:
    image_paths: List[Path] = []

    for idx, scene in enumerate(scenes, start=1):
        image_prompt = f"{style} storyboard frame, {scene}, cinematic composition, detailed digital art"
        try:
            image = client.text_to_image(
                prompt=image_prompt,
                model=image_model,
                width=1024,
                height=576,
            )
        except Exception as exc:  # noqa: BLE001
            raise SceneImageGenerationError(
                f"Scene {idx} image generation failed with model '{image_model}'. "
                "Check HF_TOKEN, model availability, and access permissions. "
                f"Original error: {exc}",
                image_paths=image_paths,
            ) from exc

        image_path = OUTPUTS_DIR / f"{run_stamp}_scene_{idx}.png"
        image.save(image_path)
        image_paths.append(image_path)

    return image_paths


def make_slideshow_video(image_paths: List[Path], run_stamp: str, fps: int = 6, scene_duration_sec: int = 3) -> Path:
    if not image_paths:
        raise RuntimeError("No scene images were created, so MP4 rendering cannot start.")

    output_path = OUTPUTS_DIR / f"{run_stamp}.mp4"
    concat_file = OUTPUTS_DIR / f"{run_stamp}_concat.txt"
    scene_duration_sec = max(1, int(scene_duration_sec))

    lines = []
    for image_path in image_paths:
        lines.append(f"file '{image_path.name}'")
        lines.append(f"duration {scene_duration_sec}")
    lines.append(f"file '{image_paths[-1].name}'")
    concat_file.write_text("\n".join(lines), encoding="utf-8")

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg_exe,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-c:v",
        "png",
        "-i",
        concat_file.name,
        "-vf",
        f"fps={max(1, int(fps))}",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, cwd=OUTPUTS_DIR)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        raise RuntimeError(f"FFmpeg MP4 rendering failed: {detail}") from exc
    finally:
        concat_file.unlink(missing_ok=True)

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("MP4 file was not created correctly. Please try again.")

    return output_path


def generate_storyboard_video(prompt: str, style: str, text_model: str, image_model: str):
    """Run the full generation pipeline.

    Returns:
        tuple[str, str, str, list[str]]: (status_text, storyboard_text, video_path, scene_image_paths).
        On failures, `video_path` is an empty string and `scene_image_paths` may be partial.
    """
    prompt = (prompt or "").strip()
    style = (style or "").strip()

    if not prompt:
        return (
            "Please enter a prompt before generating.",
            "",
            "",
            [],
        )

    client, token = _create_client()
    if not token:
        return (
            "HF_TOKEN is not set. Set it as an environment variable, then retry. "
            "Example (PowerShell): setx HF_TOKEN \"hf_xxx\" and restart the terminal.",
            "",
            "",
            [],
        )

    run_stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    try:
        storyboard_text, scenes = generate_storyboard(client, prompt, style, text_model)
    except Exception as exc:  # noqa: BLE001
        return (
            f"Storyboard generation failed: {exc}",
            "",
            "",
            [],
        )

    try:
        image_paths = generate_scene_images(client, scenes, style, image_model, run_stamp)
    except SceneImageGenerationError as exc:
        return (
            f"Image generation failed: {exc}",
            storyboard_text,
            "",
            [str(path) for path in exc.image_paths],
        )
    except Exception as exc:  # noqa: BLE001
        return (
            f"Image generation failed: {exc}",
            storyboard_text,
            "",
            [],
        )

    try:
        video_path = make_slideshow_video(image_paths, run_stamp)
    except Exception as exc:  # noqa: BLE001
        return (
            f"Video rendering failed: {exc}",
            storyboard_text,
            "",
            [str(path) for path in image_paths],
        )

    return (
        f"Success: Created storyboard slideshow MP4 at {video_path}",
        storyboard_text,
        str(video_path),
        [str(path) for path in image_paths],
    )


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Magic Clone Local") as demo:
        gr.Markdown(
            "# Magic Clone Local\n"
            "Generate a 3-scene storyboard and export it as a slideshow MP4.\n\n"
            "**Note:** This produces a storyboard slideshow video (still images), not full motion animation."
        )

        with gr.Row():
            prompt = gr.Textbox(label="Story prompt", lines=4, placeholder="A brave fox explores a neon forest at dusk")
            style = gr.Textbox(label="Visual style", value="cinematic concept art")

        with gr.Accordion("Advanced settings", open=False):
            text_model = gr.Textbox(label="Text model", value=DEFAULT_TEXT_MODEL)
            image_model = gr.Textbox(label="Image model", value=DEFAULT_IMAGE_MODEL)

        run_btn = gr.Button("Generate storyboard + MP4", variant="primary")

        status = gr.Textbox(label="Status", lines=3)
        storyboard = gr.Textbox(label="Storyboard", lines=8)
        video = gr.Video(label="Storyboard slideshow MP4")
        gallery = gr.Gallery(label="Scene images", columns=3, height=260)

        run_btn.click(
            fn=generate_storyboard_video,
            inputs=[prompt, style, text_model, image_model],
            outputs=[status, storyboard, video, gallery],
        )

    return demo


if __name__ == "__main__":
    app = build_ui()
    app.launch()
