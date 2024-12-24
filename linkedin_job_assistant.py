import streamlit as st
import os
from dotenv import load_dotenv
from groq import Groq
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import PyPDF2
import docx

# Load environment variables
load_dotenv()

# Initialize Groq client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

if not GROQ_API_KEY:
    st.error("GROQ_API_KEY is not set in the environment variables.")
    st.stop()

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

class ResumeParser:
    def extract_text_from_pdf(self, file):
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text

    def extract_text_from_docx(self, file):
        doc = docx.Document(file)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text

    def parse_resume(self, file):
        file_type = file.name.split('.')[-1].lower()
        if file_type == 'pdf':
            return self.extract_text_from_pdf(file)
        elif file_type in ['docx', 'doc']:
            return self.extract_text_from_docx(file)
        else:
            raise ValueError("Unsupported file format")

def analyze_resume_with_groq(resume_text):
    prompt = f"""
    Analyze the following resume and extract:
    1. Key skills
    2. Years of experience
    3. Job titles
    4. Education
    5. Core competencies

    Resume:
    {resume_text}

    Provide the analysis in a structured format.
    """

    messages = [{"role": "user", "content": prompt}]
    completion = client.chat.completions.create(
        model="llama-3.2-90b-vision-preview",
        messages=messages,
        temperature=0.7,
        max_tokens=2048,
    )
    
    return completion.choices[0].message.content

def match_job_with_resume(job_description, resume_analysis):
    prompt = f"""
    Analyze the job description and resume analysis below and determine:
    1. Match percentage (0-100)
    2. Key matching skills
    3. Missing skills
    4. Recommendations for application

    Job Description:
    {job_description}

    Resume Analysis:
    {resume_analysis}

    Provide a structured analysis of the match.
    """

    messages = [{"role": "user", "content": prompt}]
    completion = client.chat.completions.create(
        model="llama-3.2-90b-vision-preview",
        messages=messages,
        temperature=0.7,
        max_tokens=2048,
    )
    
    return completion.choices[0].message.content

class LinkedInJobScraper:
    def __init__(self):
        self.driver = None

    def setup_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        self.driver = webdriver.Chrome(options=options)

    def login_to_linkedin(self):
        self.driver.get("https://www.linkedin.com/login")
        
        email_field = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        email_field.send_keys(LINKEDIN_EMAIL)
        
        password_field = self.driver.find_element(By.ID, "password")
        password_field.send_keys(LINKEDIN_PASSWORD)
        
        login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()
        time.sleep(3)

    def search_jobs(self, keywords, location):
        jobs = []
        search_url = f"https://www.linkedin.com/jobs/search/?keywords={keywords}&location={location}"
        self.driver.get(search_url)
        
        # Wait for job cards to load
        time.sleep(3)
        
        job_cards = self.driver.find_elements(By.CLASS_NAME, "job-card-container")
        
        for card in job_cards[:10]:  # Limit to first 10 jobs
            try:
                title = card.find_element(By.CLASS_NAME, "job-card-list__title").text
                company = card.find_element(By.CLASS_NAME, "job-card-container__company-name").text
                location = card.find_element(By.CLASS_NAME, "job-card-container__metadata-item").text
                link = card.find_element(By.CLASS_NAME, "job-card-list__title").get_attribute("href")
                
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "link": link
                })
            except Exception as e:
                continue
                
        return jobs

class LinkedInAutoApply:
    def __init__(self):
        self.driver = None
        self.applied_jobs = set()

    def setup_driver(self):
        options = webdriver.ChromeOptions()
        # Remove headless mode to handle complex interactions
        self.driver = webdriver.Chrome(options=options)
        
    def login_to_linkedin(self):
        try:
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(3)
            
            # Enter email
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            email_field.send_keys(LINKEDIN_EMAIL)
            
            # Enter password
            password_field = self.driver.find_element(By.ID, "password")
            password_field.send_keys(LINKEDIN_PASSWORD)
            
            # Click login button
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            # Wait for login to complete
            time.sleep(5)
            
            # Verify login success
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".feed-identity-module"))
                )
                st.success("Successfully logged in to LinkedIn")
            except:
                st.error("Failed to verify login success")
                
        except Exception as e:
            st.error(f"Login failed: {str(e)}")
            raise Exception("LinkedIn login failed")

    def search_jobs(self, keywords, location):
        jobs = []
        try:
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={keywords}&location={location}"
            self.driver.get(search_url)
            time.sleep(3)
            
            # Wait for job listings to load
            job_cards = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "job-card-container"))
            )
            
            for card in job_cards[:10]:  # Limit to first 10 jobs
                try:
                    title = card.find_element(By.CLASS_NAME, "job-card-list__title").text
                    company = card.find_element(By.CLASS_NAME, "job-card-container__company-name").text
                    location = card.find_element(By.CLASS_NAME, "job-card-container__metadata-item").text
                    link = card.find_element(By.CLASS_NAME, "job-card-list__title").get_attribute("href")
                    
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "link": link
                    })
                except Exception as e:
                    st.warning(f"Error parsing job card: {str(e)}")
                    continue
                    
            return jobs
            
        except Exception as e:
            st.error(f"Error searching jobs: {str(e)}")
            return []

    def apply_to_job(self, job_url, resume_path):
        try:
            self.driver.get(job_url)
            time.sleep(2)
            
            # Find and click the apply button
            apply_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button[data-control-name='jobdetails_topcard_inapply']"))
            )
            apply_button.click()
            time.sleep(2)
            
            # Check if it's an Easy Apply job
            try:
                # Handle file upload if required
                upload_button = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
                )
                upload_button.send_keys(resume_path)
                time.sleep(2)
                
                # Click through the application steps
                while True:
                    try:
                        next_button = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "button[aria-label='Continue to next step']"))
                        )
                        next_button.click()
                        time.sleep(1)
                    except:
                        break
                
                # Submit application
                submit_button = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "button[aria-label='Submit application']"))
                )
                submit_button.click()
                time.sleep(2)
                
                return True, "Successfully applied"
                
            except Exception as e:
                return False, f"Not an Easy Apply job or error occurred: {str(e)}"
                
        except Exception as e:
            return False, f"Error applying to job: {str(e)}"

def evaluate_job_match(job_details, resume_analysis, min_match_percentage=70):
    prompt = f"""
    Analyze the job requirements and resume to determine if this is a good match:
    
    Job Details:
    {job_details}
    
    Resume Analysis:
    {resume_analysis}
    
    Return a JSON with:
    1. match_percentage (0-100)
    2. matching_skills (list)
    3. missing_skills (list)
    4. should_apply (boolean based on {min_match_percentage}% minimum match)
    5. reason (string explaining the decision)
    """
    
    messages = [{"role": "user", "content": prompt}]
    completion = client.chat.completions.create(
        model="llama-3.2-90b-vision-preview",
        messages=messages,
        temperature=0.7,
        max_tokens=2048,
    )
    
    return completion.choices[0].message.content

def main():
    st.title("LinkedIn Automatic Job Application Assistant")
    
    # File upload for resume
    uploaded_file = st.file_uploader("Upload your resume (PDF or DOCX)", type=['pdf', 'docx'])
    resume_path = st.text_input("Enter the path to your resume file for automatic applications:")
    
    # Job search parameters
    col1, col2 = st.columns(2)
    with col1:
        keywords = st.text_input("Job Title/Keywords (e.g., 'Python Developer')")
        location = st.text_input("Location (e.g., 'San Francisco, CA')")
    with col2:
        experience = st.slider("Years of Experience", 0, 20, 5)
        min_match = st.slider("Minimum Match Percentage", 50, 100, 70)
    
    if uploaded_file and resume_path:
        with st.spinner("Analyzing your resume..."):
            parser = ResumeParser()
            resume_text = parser.parse_resume(uploaded_file)
            resume_analysis = analyze_resume_with_groq(resume_text)
            
        st.subheader("Resume Analysis")
        st.write(resume_analysis)
        
        if st.button("Start Automatic Job Search and Apply"):
            auto_applier = LinkedInAutoApply()
            auto_applier.setup_driver()
            auto_applier.login_to_linkedin()
            
            with st.spinner("Searching and applying to matching jobs..."):
                jobs = auto_applier.search_jobs(keywords, location)
                
                # Create a progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, job in enumerate(jobs):
                    # Update progress
                    progress = (idx + 1) / len(jobs)
                    progress_bar.progress(progress)
                    status_text.text(f"Processing job {idx + 1} of {len(jobs)}")
                    
                    # Evaluate job match
                    match_result = evaluate_job_match(job, resume_analysis, min_match)
                    
                    # Create expander for job details
                    with st.expander(f"{job['title']} at {job['company']}"):
                        st.write(f"Location: {job['location']}")
                        st.write(f"Match Analysis:")
                        st.write(match_result)
                        
                        # Auto apply if match percentage is above threshold
                        if match_result['should_apply']:
                            success, message = auto_applier.apply_to_job(job['link'], resume_path)
                            if success:
                                st.success(f"Successfully applied to {job['company']}")
                            else:
                                st.warning(f"Could not apply: {message}")
                        else:
                            st.info("Skipped - Below match threshold")
                
                status_text.text("Completed job search and application process!")

if __name__ == "__main__":
    main() 