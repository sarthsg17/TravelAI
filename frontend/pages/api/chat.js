import { TravelChatbot } from '../../../ai_services/nlp_chatbot';

// Initialize chatbot instance with environment variables
const chatbot = new TravelChatbot({
  openaiApiKey: process.env.OPENAI_API_KEY,
  systemPrompt: "You are a helpful travel assistant. Provide concise, accurate information about travel destinations, itineraries, and recommendations."
});

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { message, chatHistory } = req.body;
    
    // Add context from user's trip data if available
    const context = req.headers['x-trip-context'] || '';
    
    const response = await chatbot.respond({
      query: message,
      chatHistory: chatHistory || [],
      context
    });

    res.status(200).json({
      response,
      chatId: Date.now() // Return unique chat identifier
    });
  } catch (error) {
    console.error('Chat error:', error);
    res.status(500).json({ 
      error: 'Failed to process chat request',
      details: error.message 
    });
  }
}