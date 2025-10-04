import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import os

def add_text_to_image(image, text, height_from_base, font_size=40, font_color="white", 
                      use_background=True, background_color="#000000", background_opacity=50, background_padding=10):
    """
    Add text continuously horizontally across the image at a specified height from the base
    """
    # Create a copy of the image to avoid modifying the original
    img_copy = image.copy()
    draw = ImageDraw.Draw(img_copy)
    
    # Try to use a default font, fallback to basic font if not available
    try:
        font = ImageFont.truetype("Arial.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    # Get image dimensions
    img_width, img_height = img_copy.size
    
    # Calculate text dimensions
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    # Add some spacing between repeated text
    spacing = 20
    total_text_width = text_width + spacing
    
    # Calculate Y position (height from base)
    y = img_height - height_from_base - text_height
    
    # Add background if enabled
    if use_background:
        # Convert hex color to RGB
        bg_color = tuple(int(background_color[i:i+2], 16) for i in (1, 3, 5))
        # Calculate opacity (0-255 from 0-100%)
        opacity = int((background_opacity / 100) * 255)
        
        # Create a semi-transparent overlay
        overlay = Image.new('RGBA', img_copy.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        background_coords = [
            0,
            y - background_padding,
            img_width,
            y + text_height + background_padding
        ]
        overlay_draw.rectangle(background_coords, fill=(*bg_color, opacity))
        
        # Composite the overlay onto the image
        img_copy = Image.alpha_composite(img_copy.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img_copy)
    
    # Calculate how many times the text can fit across the image width
    num_repetitions = (img_width // total_text_width) + 2  # +2 to ensure full coverage
    
    # Draw the text repeatedly across the width
    for i in range(num_repetitions):
        x = i * total_text_width
        # Only draw if the text starts within the image bounds
        if x < img_width:
            draw.text((x, y), text, fill=font_color, font=font)
    
    return img_copy

def create_zip_file(processed_images, original_filenames):
    """
    Create a zip file containing all processed images
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for i, (img, filename) in enumerate(zip(processed_images, original_filenames)):
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            # Create a new filename with '_processed' suffix
            name, ext = os.path.splitext(filename)
            new_filename = f"{name}_processed.png"
            
            zip_file.writestr(new_filename, img_buffer.getvalue())
    
    zip_buffer.seek(0)
    return zip_buffer

def main():
    st.set_page_config(
        page_title="Photo Text Overlay App",
        page_icon="📸",
        layout="wide"
    )
    
    st.title("📸 Photo Text Overlay App")
    st.markdown("Upload multiple photos and add text continuously across the width at a specified height from the base!")
    
    # Sidebar for text configuration
    st.sidebar.header("Text Configuration")
    text_input = st.sidebar.text_input("Enter text to add:", value="Sample Text")
    height_from_base = st.sidebar.slider(
        "Height from base (pixels)", 
        min_value=10, 
        max_value=500, 
        value=100,
        help="Distance from the bottom of the image where text will be placed"
    )
    font_size = st.sidebar.slider("Font size", min_value=10, max_value=100, value=40)
    font_color = st.sidebar.color_picker("Font color", value="#FFFFFF")
    
    # Background configuration
    st.sidebar.header("Background Configuration")
    use_background = st.sidebar.checkbox("Add background to text", value=True)
    background_color = st.sidebar.color_picker("Background color", value="#000000")
    background_opacity = st.sidebar.slider("Background opacity (%)", min_value=0, max_value=100, value=50)
    background_padding = st.sidebar.slider("Background padding", min_value=0, max_value=30, value=10)
    
    # Initialize session state for file uploader
    if 'clear_files' not in st.session_state:
        st.session_state.clear_files = False
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose image files",
        type=['png', 'jpg', 'jpeg'],
        accept_multiple_files=True,
        help="You can upload up to 15 images at once",
        key="file_uploader" if not st.session_state.clear_files else "file_uploader_cleared"
    )
    
    # Clear all button
    if uploaded_files:
        if st.button("🗑️ Clear All Images", type="secondary"):
            st.session_state.clear_files = not st.session_state.clear_files
            st.rerun()
    
    if uploaded_files:
        if len(uploaded_files) > 15:
            st.error(f"⚠️ You have uploaded {len(uploaded_files)} images. Please upload no more than 15 images at once.")
            st.stop()
        
        st.success(f"Uploaded {len(uploaded_files)} image(s)")
        
        # Process images
        if st.button("Process Images", type="primary"):
            processed_images = []
            original_filenames = []
            
            # Create progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Create columns for displaying images
            cols = st.columns(min(3, len(uploaded_files)))
            
            for i, uploaded_file in enumerate(uploaded_files):
                try:
                    # Update progress
                    progress = (i + 1) / len(uploaded_files)
                    progress_bar.progress(progress)
                    status_text.text(f"Processing {uploaded_file.name}...")
                    
                    # Open and process image
                    image = Image.open(uploaded_file)
                    
                    # Convert to RGB if necessary (for PNG with transparency)
                    if image.mode in ('RGBA', 'LA'):
                        background = Image.new('RGB', image.size, (255, 255, 255))
                        background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                        image = background
                    elif image.mode != 'RGB':
                        image = image.convert('RGB')
                    
                    # Add text to image
                    processed_image = add_text_to_image(
                        image, 
                        text_input, 
                        height_from_base, 
                        font_size, 
                        font_color,
                        use_background,
                        background_color,
                        background_opacity,
                        background_padding
                    )
                    
                    processed_images.append(processed_image)
                    original_filenames.append(uploaded_file.name)
                    
                    # Display in columns
                    col_idx = i % 3
                    with cols[col_idx]:
                        st.image(processed_image, caption=f"Processed: {uploaded_file.name}", use_container_width=True)
                
                except Exception as e:
                    st.error(f"Error processing {uploaded_file.name}: {str(e)}")
            
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
            
            if processed_images:
                st.success(f"Successfully processed {len(processed_images)} image(s)!")
                
                # Create download button for zip file
                zip_buffer = create_zip_file(processed_images, original_filenames)
                st.download_button(
                    label="📥 Download All Processed Images (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="processed_images.zip",
                    mime="application/zip"
                )
                
                # Individual download buttons
                st.subheader("Individual Downloads")
                download_cols = st.columns(min(3, len(processed_images)))
                
                for i, (img, filename) in enumerate(zip(processed_images, original_filenames)):
                    col_idx = i % 3
                    with download_cols[col_idx]:
                        img_buffer = io.BytesIO()
                        img.save(img_buffer, format='PNG')
                        img_buffer.seek(0)
                        
                        name, ext = os.path.splitext(filename)
                        new_filename = f"{name}_processed.png"
                        
                        st.download_button(
                            label=f"📥 {new_filename}",
                            data=img_buffer.getvalue(),
                            file_name=new_filename,
                            mime="image/png",
                            key=f"download_{i}"
                        )
    
    else:
        st.info("👆 Please upload one or more image files to get started!")
        
        
if __name__ == "__main__":
    main()