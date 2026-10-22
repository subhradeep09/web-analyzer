import os
import cv2
from PIL import Image
from playwright.sync_api import sync_playwright
import json
import sys
from pathlib import Path
from prettytable import PrettyTable
from io import BytesIO

# Add local imports
sys.path.append(str(Path(__file__).parent))
from gemini import analyze_websites_with_gemini
from cloudinary_storage import init_cloudinary, upload_image, upload_website_screenshots

# Initialize Cloudinary if environment variables are set
init_cloudinary()

# Helper function to ensure consistent response structure for the frontend
def ensure_frontend_compatibility(scores):
    """
    Ensure the response structure is compatible with the frontend expectations.
    The frontend expects each section to have entries with name, score, and criteria.
    """
    for section_type in ["header", "main", "footer", "full"]:
        if section_type in scores:
            for entry in scores[section_type]:
                # Ensure criteria exists
                if "criteria" not in entry:
                    score_value = entry.get("score", 0.5)
                    entry["criteria"] = {
                        "Clarity": score_value,
                        "Modernity": score_value,
                        "Relevance": score_value,
                        "Consistency": score_value,
                        "Visual Appeal": score_value
                    }
    return scores

# --- OpenCV Preprocessing ---
def preprocess_image(image_path):
    try:
        # Read the image
        image = cv2.imread(image_path)
        if image is None:
            print(f"Failed to read image from {image_path}")
            return None
            
        # Process the image
        enhanced_image = cv2.equalizeHist(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
        resized_image = cv2.resize(enhanced_image, (1280, 720))
        final_image = cv2.cvtColor(resized_image, cv2.COLOR_GRAY2BGR)
        
        # Create processed image path
        processed_image_path = image_path.replace(".png", "_processed.png")
        
        # Write the processed image
        cv2.imwrite(processed_image_path, final_image)
        
        return processed_image_path
    except Exception as e:
        print(f"Error preprocessing image {image_path}: {str(e)}")
        return None

def capture_sections_and_fullpage(page, url, website_name):
    try:
        # Sanitize URL
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        print(f"[INFO] Navigating to {url} for {website_name}...")
        page.goto(url, wait_until="load", timeout=60000)
        page.wait_for_timeout(3000)

        selectors = {
            "header": [
                'header', 'nav', 'div[role="banner"]', '.header', '.navbar', '#header',
                '#nav-main', '#navbar', '.top-bar', '.main-header', '.global-header',
                'div[data-role="header"]', '.site-header', 'div[class*="header"]',
                'div[class*="navbar"]', 'div[class*="top"]', '#masthead', '.page-header',
                '#site-header', '#main-header', '.app-header', '.layout-header', '#branding',
                'ytd-masthead', 'ytd-app > #masthead-container'
            ],
            "footer": [
                'footer', '.footer', '#footer', '#navFooter', '.site-footer', '.bottom-bar',
                'div[role="contentinfo"]', '.main-footer', '.global-footer', '.footer-wrapper',
                'div[class*="footer"]', 'div[class*="bottom"]', 'div[data-role="footer"]',
                '.site-info', '#colophon', '#page-footer', '.app-footer', '.layout-footer',
                'ytd-footer', 'ytd-app > #footer'
            ]
        }

        # Create directory for screenshots
        screenshots_folder = f"screenshots/{website_name}"
        os.makedirs(screenshots_folder, exist_ok=True)

        # Create paths for local storage
        header_path = f"{screenshots_folder}/{website_name}_header.png"
        main_path = f"{screenshots_folder}/{website_name}_main.png"
        footer_path = f"{screenshots_folder}/{website_name}_footer.png"
        full_page_path = f"{screenshots_folder}/{website_name}_full.png"

        # 1. Take full page screenshot FIRST (essential for Gemini)
        full_img_bytes = page.screenshot(full_page=True)
        with open(full_page_path, "wb") as f:
            f.write(full_img_bytes)

        # 2. Header detection with fallback
        header = next((el for sel in selectors["header"] if (el := page.query_selector(sel))), None)
        header_box = header.bounding_box() if header else None
        header_bottom = 200

        if header and header_box and header_box.get('height', 0) > 20:
            try:
                header_img_bytes = header.screenshot()
                with open(header_path, "wb") as f:
                    f.write(header_img_bytes)
                header_bottom = header_box['y'] + header_box['height']
            except Exception:
                header_img_bytes = page.screenshot(clip={'x': 0, 'y': 0, 'width': 1280, 'height': 200})
                with open(header_path, "wb") as f:
                    f.write(header_img_bytes)
        else:
            print(f"[INFO] Using viewport top as header fallback for {website_name}")
            header_img_bytes = page.screenshot(clip={'x': 0, 'y': 0, 'width': 1280, 'height': 200})
            with open(header_path, "wb") as f:
                f.write(header_img_bytes)

        # 3. Footer detection with fallback
        footer = next((el for sel in selectors["footer"] if (el := page.query_selector(sel))), None)
        footer_box = footer.bounding_box() if footer else None
        viewport_size = page.viewport_size or {"width": 1280, "height": 800}
        footer_top = max(header_bottom + 100, viewport_size['height'] - 250)

        if footer and footer_box and footer_box.get('height', 0) > 20:
            try:
                footer_img_bytes = footer.screenshot()
                with open(footer_path, "wb") as f:
                    f.write(footer_img_bytes)
                footer_top = footer_box['y']
            except Exception:
                footer_img_bytes = page.screenshot(clip={'x': 0, 'y': max(0, viewport_size['height'] - 250), 'width': 1280, 'height': 250})
                with open(footer_path, "wb") as f:
                    f.write(footer_img_bytes)
        else:
            print(f"[INFO] Using bottom viewport as footer fallback for {website_name}")
            footer_img_bytes = page.screenshot(clip={'x': 0, 'y': max(0, viewport_size['height'] - 250), 'width': 1280, 'height': 250})
            with open(footer_path, "wb") as f:
                f.write(footer_img_bytes)

        # 4. Main content section
        main_height = max(0, footer_top - header_bottom)
        if main_height > 50:
            try:
                main_img_bytes = page.screenshot(clip={
                    'x': 0,
                    'y': header_bottom,
                    'width': 1280,
                    'height': min(main_height, 1600)
                })
                with open(main_path, "wb") as f:
                    f.write(main_img_bytes)
            except Exception:
                main_path = full_page_path
        else:
            main_path = full_page_path

        local_paths = {
            "header": header_path,
            "main": main_path,
            "footer": footer_path,
            "full": full_page_path
        }

        # Upload to Cloudinary if configured
        cloudinary_folder = f"website_screenshots/{website_name}"
        cloudinary_urls = {}

        if os.environ.get('CLOUDINARY_CLOUD_NAME'):
            for section, path in local_paths.items():
                if path and os.path.exists(path):
                    public_id = f"{website_name}_{section}"
                    result = upload_image(path, public_id=public_id, folder=cloudinary_folder)
                    if "error" not in result:
                        cloudinary_urls[f"{section}_cloudinary_url"] = result["url"]
                    else:
                        print(f"[WARN] Failed to upload {section} to Cloudinary: {result.get('error')}")

        return {**local_paths, **cloudinary_urls}

    except Exception as e:
        print(f"[ERROR] Error processing {website_name}: {e}")
        return None

# --- Compare websites (combined method) ---
def compare_websites_combined(websites, category):
    """
    Compare websites using only Gemini scoring.
    
    Args:
        websites: List of dictionaries with website name and URL
        category: Website category
        
    Returns:
        Dictionary with Gemini scores for each section
    """
    # Get scores from the main compare_websites function
    return compare_websites(websites, category)

def get_browser_instance(p):
    """
    Launch Chromium with Linux/Docker/Render-safe flags.
    If the Chromium browser binary is missing on Render, auto-installs it on the fly.
    """
    chromium_args = [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--no-first-run',
        '--no-zygote',
        '--single-process',
        '--disable-gpu'
    ]

    try:
        return p.chromium.launch(headless=True, args=chromium_args)
    except Exception as e:
        err_msg = str(e)
        print(f"[WARN] Failed to launch Chromium: {err_msg}")
        if "Executable doesn't exist" in err_msg or "playwright install" in err_msg:
            print("[INFO] Playwright Chromium executable missing. Downloading now...")
            import subprocess
            try:
                subprocess.run(["playwright", "install", "chromium"], check=True)
                return p.chromium.launch(headless=True, args=chromium_args)
            except Exception as inst_err:
                print(f"[ERROR] Auto-install failed: {inst_err}")

        # Try Firefox only as secondary fallback if installed
        try:
            return p.firefox.launch(headless=True)
        except Exception:
            pass

        raise Exception(f"Playwright browser launch failed: {err_msg}")

# --- Compare websites (main method) ---
def compare_websites(websites, category):
    """
    Compare websites using only Gemini scores.
    
    Args:
        websites: List of dictionaries with website name and URL
        category: Website category
        
    Returns:
        Dictionary with scores for each section using only Gemini
    """
    all_scores = {"header": [], "main": [], "footer": [], "full": []}
    website_data = []
    
    # First, capture screenshots and collect website data
    with sync_playwright() as p:
        browser = get_browser_instance(p)
        context = browser.new_context(viewport={"width": 1280, "height": 3000})

        for site in websites:
            name = site['name']
            url = site['url']
            page = context.new_page()
            try:
                sections = capture_sections_and_fullpage(page, url, name)
                if sections:
                    website_data.append({
                        "name": name,
                        "url": url,
                        "sections": sections
                    })
            except Exception as e:
                print(f"[ERROR] Failed to process {name}: {str(e)}")
            finally:
                page.close()

        browser.close()
    
    # Check if we have any successful website data
    if not website_data:
        print("No website data available for analysis")
        return all_scores
    
    # Now get Gemini scores for full-page analysis of sections
    print("\nGetting Gemini scores...")
    
    # Prepare input for Gemini API
    gemini_input = []
    for site in website_data:
        sections = site.get("sections", {})
        full_path = sections.get("full")
        
        gemini_site = {
            "name": site["name"],
            "url": site["url"]
        }
        
        # Include both local path and Cloudinary URL
        if full_path:
            gemini_site["full_path"] = full_path
        full_cloudinary_url = sections.get("full_cloudinary_url")
        if full_cloudinary_url:
            gemini_site["full_cloudinary_url"] = full_cloudinary_url
            
        gemini_input.append(gemini_site)
    
    # Call Gemini API to get vision improvements and section scores
    gemini_results = analyze_websites_with_gemini(gemini_input, category)
    
    # Extract websites from Gemini results
    gemini_website_data = {}
    if "websites" in gemini_results:
        for website in gemini_results["websites"]:
            name = website.get("name")
            gemini_website_data[name] = website
    
    # Add vision improvements directly to the result
    all_scores["websites"] = gemini_results.get("websites", [])
    all_scores["comparison"] = gemini_results.get("comparison", {})
    
    # Process Gemini scores for each section
    for name, website in gemini_website_data.items():
        sections = website.get("sections", {})
        overall_score = website.get("overall_score", 0) / 10.0  # Convert to 0-1 scale
        
        # Map Gemini section names to our section types
        section_mapping = {
            "header": "header",
            "main_content": "main",
            "footer": "footer"
        }
        
        # Find the paths from website_data
        site_sections = None
        for site in website_data:
            if site["name"] == name:
                site_sections = site["sections"]
                break
        
        if not site_sections:
            continue
            
        # Process full page score
        full_path = site_sections.get("full")
        full_cloudinary_url = site_sections.get("full_cloudinary_url")
        
        if full_path:
            entry = {
                "name": name,
                "path": full_path,
                "score": overall_score,
                "gemini_score": overall_score,
                "details": website,
                "criteria": {
                    "Clarity": overall_score,
                    "Modernity": overall_score,
                    "Relevance": overall_score,
                    "Consistency": overall_score,
                    "Visual Appeal": overall_score
                }
            }
            
            if full_cloudinary_url:
                entry["cloudinary_url"] = full_cloudinary_url
                
            all_scores["full"].append(entry)
            
        # Process section scores
        for gemini_section, our_section in section_mapping.items():
            if gemini_section in sections:
                section_data = sections[gemini_section]
                section_score = section_data.get("score", 0) / 10.0  # Convert to 0-1 scale
                
                section_path = site_sections.get(our_section)
                section_cloudinary_url = site_sections.get(f"{our_section}_cloudinary_url")
                
                if section_path:
                    entry = {
                        "name": name,
                        "path": section_path,
                        "score": section_score,
                        "gemini_score": section_score,
                        "criteria": {
                            "Clarity": section_score,
                            "Modernity": section_score,
                            "Relevance": section_score,
                            "Consistency": section_score,
                            "Visual Appeal": section_score
                        }
                    }
                    
                    # Add strengths and weaknesses
                    entry["gemini_strengths"] = section_data.get("strengths", [])
                    entry["gemini_weaknesses"] = section_data.get("weaknesses", [])
                    entry["gemini_recommendations"] = section_data.get("recommendations", [])
                    
                    if section_cloudinary_url:
                        entry["cloudinary_url"] = section_cloudinary_url
                        
                    all_scores[our_section].append(entry)
    
    # Print summary table
    print("\n=== FINAL SUMMARY ===")
    print(f"{'Website':<10} {'Header':<10} {'Main':<10} {'Footer':<10} {'Overall':<10}")
    print("-" * 50)
    
    website_summaries = {}
    for section_type in ["header", "main", "footer", "full"]:
        for entry in all_scores[section_type]:
            name = entry.get("name")
            if name not in website_summaries:
                website_summaries[name] = {}
            website_summaries[name][section_type] = entry.get("score", 0)
    
    for name, sections in website_summaries.items():
        header = sections.get("header", 0)
        main = sections.get("main", 0)
        footer = sections.get("footer", 0)
        overall = sections.get("full", 0)
        
        print(f"{name:<10} {header:<10.3f} {main:<10.3f} {footer:<10.3f} {overall:<10.3f}")

    # Ensure the response structure is compatible with the frontend
    all_scores = ensure_frontend_compatibility(all_scores)
    
    # Debug: Print the structure of the response
    print("\nDEBUG - Response Structure:")
    for section in all_scores.keys():
        print(f"Section: {section}")
        if isinstance(all_scores[section], list):
            for item in all_scores[section]:
                print(f"  - {item.get('name')}: {item.keys()}")
    
    return all_scores

# Example usage
if __name__ == "__main__":
    websites = [
        {"name": "Amazon", "url": "https://www.amazon.com"},
        {"name": "Flipkart", "url": "https://www.flipkart.com"},
        {"name": "Blinkit", "url": "https://blinkit.com"}
    ]
    
    print("Comparing websites with combined CLIP and Gemini analysis...")
    results = compare_websites_combined(websites, "e-commerce")
    
    # Print results
    print("\nDetailed JSON Results:")
    print(json.dumps(results, indent=2))
