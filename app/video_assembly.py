import os
import json
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pydub import AudioSegment

def wrap_text(text, font, max_width):
    words = text
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        temp_img = Image.new("RGB", (1000, 100), color="white")
        temp_draw = ImageDraw.Draw(temp_img)
        temp_draw.text((0, 0), test_line, font=font, fill="black")
        bbox = temp_img.getbbox()
        textwidth = bbox[2] if bbox else 0
        if textwidth <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)
    return lines

def get_audio_duration(audio_path):
    try:
        audio = AudioSegment.from_mp3(audio_path)
        return len(audio) / 1000.0
    except Exception as e:
        print(f"Error getting audio duration: {e}")
        return 5.0

def create_slide_video(image_path, voiceover_path, output_video_path, duration):
    try:
        command = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", image_path,
            "-i", voiceover_path,
            "-c:v", "libx264", "-t", str(duration),
            "-pix_fmt", "yuv420p", output_video_path
        ]
        subprocess.run(command, check=True)
        return output_video_path
    except subprocess.CalledProcessError as e:
        print(f"Error creating slide video: {e}")
        return None

def create_structured_slide_image(heading, image_path, output_path, points, slide_index):
    try:
        img = Image.new("RGB", (1280, 720), color="white")
        draw = ImageDraw.Draw(img)

        # Heading
        try:
            font_heading = ImageFont.truetype("arial.ttf", 40)
        except IOError:
            font_heading = ImageFont.load_default()
        heading_x, heading_y = 640, 50
        draw.text((heading_x, heading_y), heading, fill="black", font=font_heading, anchor="mm")
        # Underline the heading
        heading_bbox = draw.textbbox((heading_x, heading_y), heading, font=font_heading, anchor="mm")
        underline_y = heading_bbox[3] + 5  # 5 pixels below the text
        draw.line([(heading_bbox[0] - 10, underline_y), (heading_bbox[2] + 10, underline_y)], fill="red", width=3)

        # Text Content
        font_text = ImageFont.truetype("arialbd.ttf", 30)
        text_x, text_y = 60, 210

        colors = ["blue", "gold", "green"]
        text_color = colors[(slide_index - 1) % len(colors)] # Calculate color based on slide index.

        for point in points:
            draw.text((text_x, text_y), point, fill=text_color, font=font_text)
            text_y += 65  # Adjust vertical spacing

        # Image (Right Side)
        if image_path and os.path.exists(image_path):
            image = Image.open(image_path).convert("RGBA")
            image_area = (650, 100, 1230, 650)
            image = ImageOps.fit(image, (image_area[2] - image_area[0], image_area[3] - image_area[1]), Image.LANCZOS)
            img.paste(image, image_area[:2], image)

        img.save(output_path)
        return output_path

    except Exception as e:
        print(f"Error creating structured slide image: {e}")
        return None

def concatenate_clips(clip_paths, output_path):
    try:
        command = ["ffmpeg", "-y"]
        for clip_path in clip_paths:
            command.extend(["-i", clip_path]) # Add each input file separately
        filter_complex = "".join([f"[{i}:v][{i}:a]" for i in range(len(clip_paths))]) + f"concat=n={len(clip_paths)}:v=1:a=1[v][a]"
        command.extend(["-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p", output_path])
        subprocess.run(command, check=True)
        print(f"Video assembled successfully: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error concatenating clips: {e}")

def assemble_video(assembly_file, output_video_path):
    try:
        if not os.path.exists(assembly_file):
            raise FileNotFoundError(f"Assembly file not found: {assembly_file}")
        with open(assembly_file, "r") as file:
            assembly_data = json.load(file)
        if "slides" not in assembly_data or "conclusion" not in assembly_data:
            raise KeyError("Missing required keys in JSON data")
        image_folder = "output/images"
        voice_folder = "output/voiceovers"
        temp_video_clips = []
        os.makedirs(image_folder, exist_ok=True)
        os.makedirs(voice_folder, exist_ok=True)

        # Introduction Slide (Slide 1)
        if "introduction" in assembly_data["slides"]:
            introduction_points = assembly_data["slides"]["introduction"]
            raw_image_path = f"{image_folder}/image_1.png"
            slide_image_path = f"{image_folder}/slide_1.png"
            create_structured_slide_image(
                heading=assembly_data["slides"]["title"],  # Use the title as the heading
                image_path=raw_image_path,
                output_path=slide_image_path,
                points=introduction_points,
                slide_index=1 # added slide_index
            )
            voiceover_path = f"{voice_folder}/voiceover_1.mp3"
            duration = get_audio_duration(voiceover_path)
            slide_video_path = f"output/slide_1.mp4"
            slide_video = create_slide_video(slide_image_path, voiceover_path, slide_video_path, duration)
            if slide_video:
                temp_video_clips.append(slide_video)
            else:
                print(f"Error: Could not create introduction video")
                return

        idx = 2
        # Body Slides (Slides 2-9)
        for slide in assembly_data["slides"]["sections"]:
            raw_image_path = f"{image_folder}/image_{idx}.png"
            slide_image_path = f"{image_folder}/slide_{idx}.png"
            create_structured_slide_image(
                heading=slide["heading"],
                image_path=raw_image_path,
                output_path=slide_image_path,
                points=slide["slide_points"],
                slide_index=idx # added slide_index
            )
            voiceover_path = f"{voice_folder}/voiceover_{idx}.mp3"
            duration = get_audio_duration(voiceover_path)
            slide_video_path = f"output/slide_{idx}.mp4"
            slide_video = create_slide_video(slide_image_path, voiceover_path, slide_video_path, duration)
            if slide_video:
                temp_video_clips.append(slide_video)
            else:
                print(f"Error: Could not create slide video {idx}")
                return
            idx += 1

        # Conclusion Slide (Slide 10)
        raw_image_path = f"{image_folder}/image_{idx}.png"
        slide_image_path = f"{image_folder}/slide_{idx}.png"
        create_structured_slide_image(
            heading="The End",
            image_path=raw_image_path,
            output_path=slide_image_path,
            points=assembly_data["conclusion"]["slide_points"],
            slide_index=idx # added slide_index
        )
        voiceover_path = f"{voice_folder}/voiceover_{idx}.mp3"
        duration = get_audio_duration(voiceover_path)
        slide_video_path = f"output/slide_{idx}.mp4"
        conclusion_video = create_slide_video(slide_image_path, voiceover_path, slide_video_path, duration)
        if conclusion_video:
            temp_video_clips.append(conclusion_video)
        else:
            print(f"Error: Could not create conclusion video")
            return

        concatenate_clips(temp_video_clips, output_video_path)
    except Exception as e:
        print(f"Error assembling video: {e}")