import React, { useState } from "react";
import axios from "axios";
import "./App.css";

// The URL of our FastAPI backend
const API_URL = "https://interviewiq-1-56k9.onrender.com";

// Total number of interview questions
const TOTAL_QUESTIONS = 5;

function App() {
  // ---------- State Variables ----------
  const [step, setStep] = useState(1);            // Which screen to show: 1=Upload, 2=Interview, 3=Summary
  const [sessionId, setSessionId] = useState(""); // ID returned by the backend after upload
  const [jobDescription, setJobDescription] = useState(""); // Text in the job description box
  const [resumeFile, setResumeFile] = useState(null);       // The uploaded PDF file
  const [currentQuestion, setCurrentQuestion] = useState(""); // The current interview question
  const [questionIndex, setQuestionIndex] = useState(0);     // Which question we're on (0 to 4)
  const [answer, setAnswer] = useState("");                  // Candidate's answer text
  const [summary, setSummary] = useState([]);                // List of all Q&A pairs for summary screen
  const [loading, setLoading] = useState(false);             // Show a loading spinner when true
  const [error, setError] = useState("");                    // Any error message to display

  // ---------- Step 1: Upload the resume and job description ----------
  const handleUpload = async () => {
    // Basic validation
    if (!jobDescription.trim()) {
      setError("Please enter a job description.");
      return;
    }
    if (!resumeFile) {
      setError("Please upload a resume PDF.");
      return;
    }

    setError("");
    setLoading(true);

    try {
      // Send the resume PDF and job description to the backend
      const formData = new FormData();
      formData.append("resume", resumeFile);
      formData.append("job_description", jobDescription);

      const response = await axios.post(`${API_URL}/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const newSessionId = response.data.session_id;
      setSessionId(newSessionId);

      // After uploading, immediately fetch the first question
      await fetchQuestion(newSessionId, 0);
      setStep(2); // Move to the interview screen
    } catch (err) {
      setError("Upload failed. Make sure the backend is running.");
      console.error(err);
    }

    setLoading(false);
  };

  // ---------- Fetch a question from the backend ----------
  const fetchQuestion = async (sid, index) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/ask`, {
        session_id: sid,
        question_index: index,
      });
      setCurrentQuestion(response.data.question);
      setAnswer(""); // Clear the answer box for the new question
    } catch (err) {
      setError("Failed to fetch question.");
      console.error(err);
    }
    setLoading(false);
  };

  // ---------- Step 2: Submit an answer and move to the next question ----------
  const handleNextQuestion = async () => {
    if (!answer.trim()) {
      setError("Please type an answer before continuing.");
      return;
    }

    setError("");
    setLoading(true);

    try {
      // Save the current answer to the backend
      await axios.post(`${API_URL}/answer`, {
        session_id: sessionId,
        question: currentQuestion,
        answer: answer,
      });

      const nextIndex = questionIndex + 1;

      if (nextIndex >= TOTAL_QUESTIONS) {
        // All questions done — fetch the summary
        const summaryResponse = await axios.get(`${API_URL}/summary/${sessionId}`);
        setSummary(summaryResponse.data.qa_pairs);
        setStep(3); // Move to summary screen
      } else {
        // Fetch the next question
        setQuestionIndex(nextIndex);
        await fetchQuestion(sessionId, nextIndex);
      }
    } catch (err) {
      setError("Something went wrong. Please try again.");
      console.error(err);
    }

    setLoading(false);
  };

  // ---------- Reset everything to start over ----------
  const handleStartOver = () => {
    setStep(1);
    setSessionId("");
    setJobDescription("");
    setResumeFile(null);
    setCurrentQuestion("");
    setQuestionIndex(0);
    setAnswer("");
    setSummary([]);
    setError("");
  };

  // ---------- Render ----------
  return (
    <div className="app">
      <h1 className="app-title">🎯 AI Interview Assistant</h1>

      {/* Show any error message */}
      {error && <div className="error-box">{error}</div>}

      {/* ===== STEP 1: Upload Screen ===== */}
      {step === 1 && (
        <div className="card">
          <h2>Upload Details</h2>
          <p className="subtitle">Provide the job description and the candidate's resume to begin.</p>

          <label className="field-label">Job Description</label>
          <textarea
            className="textarea"
            rows={6}
            placeholder="Paste the job description here..."
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
          />

          <label className="field-label">Resume (PDF)</label>
          <input
            type="file"
            accept=".pdf"
            className="file-input"
            onChange={(e) => setResumeFile(e.target.files[0])}
          />
          {resumeFile && <p className="file-name">📄 {resumeFile.name}</p>}

          <button className="btn" onClick={handleUpload} disabled={loading}>
            {loading ? "Uploading & Processing..." : "Start Interview →"}
          </button>
        </div>
      )}

      {/* ===== STEP 2: Interview Screen ===== */}
      {step === 2 && (
        <div className="card">
          <div className="progress">
            Question {questionIndex + 1} of {TOTAL_QUESTIONS}
          </div>

          {/* Progress bar */}
          <div className="progress-bar-bg">
            <div
              className="progress-bar-fill"
              style={{ width: `${((questionIndex + 1) / TOTAL_QUESTIONS) * 100}%` }}
            />
          </div>

          {loading ? (
            <p className="loading-text">⏳ Generating question...</p>
          ) : (
            <>
              <div className="question-box">
                <strong>Q:</strong> {currentQuestion}
              </div>

              <label className="field-label">Your Answer</label>
              <textarea
                className="textarea"
                rows={5}
                placeholder="Type your answer here..."
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
              />

              <button className="btn" onClick={handleNextQuestion} disabled={loading}>
                {questionIndex + 1 === TOTAL_QUESTIONS ? "Finish Interview ✓" : "Next Question →"}
              </button>
            </>
          )}
        </div>
      )}

      {/* ===== STEP 3: Summary Screen ===== */}
      {step === 3 && (
        <div className="card">
          <h2>Interview Complete 🎉</h2>
          <p className="subtitle">Here's a summary of all questions and answers.</p>

          {summary.map((pair, index) => (
            <div className="summary-card" key={index}>
              <p className="summary-question">
                <strong>Q{index + 1}:</strong> {pair.question}
              </p>
              <p className="summary-answer">
                <strong>A:</strong> {pair.answer}
              </p>
            </div>
          ))}

          <button className="btn btn-secondary" onClick={handleStartOver}>
            ↩ Start Over
          </button>
        </div>
      )}
    </div>
  );
}

export default App;
