import streamlit as st
import os
from dotenv import load_dotenv
from downloader import download_video, get_subtitles, save_subtitles_as_srt
from translator import translate_srt_file
from video_to_pdf import video_to_pdf

load_dotenv()

def main():
    st.title("YouTube 影片下载器与字幕转换器")

    output_dir = 'data'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 初始化 session state
    if 'default_url' not in st.session_state:
        st.session_state.default_url = "https://www.youtube.com/watch?v=-X0jBz5_gCc"
    if 'mp4_path' not in st.session_state:
        st.session_state.mp4_path = None
    if 'srt_path' not in st.session_state:
        st.session_state.srt_path = None
    if 'zh_srt_path' not in st.session_state:
        st.session_state.zh_srt_path = None
    if 'pdf_path' not in st.session_state:
        st.session_state.pdf_path = None

    url = st.text_input("请输入 YouTube 影片 URL", value=st.session_state.default_url)

    if st.button("下载视频和字幕"):
        if url:
            with st.spinner("正在下载视频和字幕..."):
                try:
                    video_id = url.split("v=")[1]

                    # 首先检查是否有字幕
                    subtitles = get_subtitles(video_id)
                    if not subtitles:
                        st.error("此视频没有可用的英文字幕，无法处理。")
                        return

                    download_progress = st.progress(0)
                    def update_download_progress(progress):
                        download_progress.progress(progress)

                    video_filename, video_path = download_video(url, output_dir, update_download_progress)
                    st.session_state.mp4_path = video_path
                    st.session_state.base_filename = os.path.splitext(video_filename)[0]

                    st.write(f"Debug: Video downloaded to {st.session_state.mp4_path}")
                    st.write(f"Debug: Base filename is {st.session_state.base_filename}")

                    st.session_state.srt_path = os.path.join(output_dir, f"{st.session_state.base_filename}.srt")
                    save_subtitles_as_srt(subtitles, st.session_state.srt_path)

                    st.write(f"Debug: Subtitles saved to {st.session_state.srt_path}")

                    st.success("视频和原始字幕下载成功！")
                except Exception as e:
                    st.error(f"下载或处理过程中发生错误: {str(e)}")
        else:
            st.warning("请输入有效的 YouTube URL")

    if st.session_state.srt_path and os.path.exists(st.session_state.srt_path):
        if st.button("翻译字幕为简体中文"):
            with st.spinner("正在翻译字幕..."):
                try:
                    deepl_api_key = os.getenv("DEEPL_API_KEY")
                    if not deepl_api_key:
                        st.error("未找到有效的 DeepL API Key。请检查 .env 文件。")
                    else:
                        st.session_state.zh_srt_path = os.path.join(output_dir, f"{st.session_state.base_filename}.zh.srt")

                        st.write(f"Debug: Translating from {st.session_state.srt_path}")
                        st.write(f"Debug: Translating to {st.session_state.zh_srt_path}")

                        # 添加翻译进度条
                        translation_progress = st.progress(0)
                        def update_translation_progress(progress):
                            translation_progress.progress(progress)

                        translate_srt_file(
                            st.session_state.srt_path,
                            st.session_state.zh_srt_path,
                            deepl_api_key,
                            progress_callback=update_translation_progress
                        )

                        if os.path.exists(st.session_state.zh_srt_path):
                            st.success("字幕翻译成功！")
                        else:
                            st.error("翻译后的文件未找到。")
                except Exception as e:
                    st.error(f"翻译失败: {str(e)}")

    if st.session_state.mp4_path and st.session_state.zh_srt_path and os.path.exists(st.session_state.zh_srt_path):
        if st.button("生成 PDF"):
            st.session_state.pdf_path = os.path.join(output_dir, f"{st.session_state.base_filename}.pdf")

            st.info("正在生成 PDF...")
            png_progress_bar = st.progress(0)
            pdf_progress_bar = st.progress(0)
            status_text = st.empty()

            def update_png_progress(progress):
                png_progress_bar.progress(progress)
                status_text.text(f"生成字幕帧进度: {progress:.1%}")

            def update_pdf_progress(progress):
                pdf_progress_bar.progress(progress)
                status_text.text(f"转换 PDF 进度: {progress:.1%}")

            try:
                pdf_created, failed_frames = video_to_pdf(
                    st.session_state.mp4_path,
                    png_progress_callback=update_png_progress,
                    pdf_progress_callback=update_pdf_progress
                )

                if os.path.exists(st.session_state.pdf_path):
                    st.success("PDF 文件创建成功！")
                else:
                    st.warning("系统无法检测到 PDF 文件，但这可能是由于权限或路径问题。如果您确定文件已创建，可以尝试手动在输出目录查找。")

                if failed_frames:
                    st.info(f"注意：在处理过程中，第 {', '.join(map(str, failed_frames))} 帧出现问题被跳过。")

            except Exception as e:
                st.error(f"PDF 转换过程中发生错误: {str(e)}")

    # 显示下载链接
    if st.session_state.mp4_path and os.path.exists(st.session_state.mp4_path):
        with open(st.session_state.mp4_path, "rb") as file:
            st.download_button(
                label="下载 MP4 文件",
                data=file,
                file_name=os.path.basename(st.session_state.mp4_path),
                mime="video/mp4"
            )

    if st.session_state.srt_path and os.path.exists(st.session_state.srt_path):
        with open(st.session_state.srt_path, "rb") as file:
            st.download_button(
                label="下载原始 SRT 字幕文件",
                data=file,
                file_name=os.path.basename(st.session_state.srt_path),
                mime="text/srt"
            )

    if st.session_state.zh_srt_path and os.path.exists(st.session_state.zh_srt_path):
        with open(st.session_state.zh_srt_path, "rb") as file:
            st.download_button(
                label="下载中文 SRT 字幕文件",
                data=file,
                file_name=os.path.basename(st.session_state.zh_srt_path),
                mime="text/srt"
            )

    # 显示 PDF 下载链接
    if st.session_state.pdf_path and os.path.exists(st.session_state.pdf_path):
        with open(st.session_state.pdf_path, "rb") as file:
            st.download_button(
                label="下载 PDF 文件",
                data=file,
                file_name=os.path.basename(st.session_state.pdf_path),
                mime="application/pdf"
            )

if __name__ == "__main__":
    main()
