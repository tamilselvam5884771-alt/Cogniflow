/**
 * API service for College Rules RAG Chatbot
 */

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');

/**
 * Check backend health and PDF indexing status
 */
export async function getHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Health check failed with status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to connect to backend health endpoint:', error);
    throw error;
  }
}

/**
 * Send a user query to the RAG chat endpoint
 * @param {string} message - Clean user question
 * @param {string|null} sessionId - Current conversation session ID
 * @returns {Promise<{success: boolean, reply: string, session_id: string, sources: Array}>}
 */
export async function sendChatMessage(message, sessionId = null) {
  try {
    const payload = {
      message: message.trim(),
      session_id: sessionId || null,
    };

    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let errorDetail = 'An unexpected server error occurred.';
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorDetail = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
        }
      } catch {
        errorDetail = `Request failed with HTTP status ${response.status}`;
      }

      const error = new Error(errorDetail);
      error.status = response.status;
      throw error;
    }

    const data = await response.json();
    return data;
  } catch (error) {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      const connErr = new Error('Cannot reach the backend server. Please verify the FastAPI server is running on ' + API_BASE_URL);
      connErr.isNetworkError = true;
      throw connErr;
    }
    throw error;
  }
}
