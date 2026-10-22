import React, { useState, useEffect } from 'react';
import WebsiteForm from './WebsiteForm';
import ResultsDisplay from './ResultsDisplay';

const AnalyzeSection = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);

  // Check for existing data on mount
  useEffect(() => {
    // Store a session key in sessionStorage to track the current browsing session
    if (!sessionStorage.getItem('sessionId')) {
      sessionStorage.setItem('sessionId', Date.now().toString());
    }
    
    // Check if we have cached data in localStorage for the current session
    const cachedData = localStorage.getItem('websiteComparisonData');
    const cachedSessionId = localStorage.getItem('websiteComparisonSessionId');
    const currentSessionId = sessionStorage.getItem('sessionId');
    
    // Only use cached data if it's from the current session
    if (cachedData && cachedSessionId === currentSessionId) {
      console.log('Using cached website comparison data from current session');
      try {
        const parsedData = JSON.parse(cachedData);
        setResults(parsedData);
        
        // Scroll to results if they exist
        setTimeout(() => {
          const resultsElement = document.getElementById('results');
          if (resultsElement) {
            resultsElement.scrollIntoView({ behavior: 'smooth' });
          }
        }, 100);
      } catch (err) {
        console.error('Error parsing cached data:', err);
      }
    }
  }, []);

  const handleSubmit = async (websites, category) => {
    setLoading(true);
    setError(null);

    //handling duplicate website entries
    const uniqueWebsites = [...new Set(websites.map(website => website.url))];
    if (uniqueWebsites.length !== websites.length) {
      setError('Please provide unique URLs for each website');
      setLoading(false);
      return;
    }
    
    const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';
    try {
      const response = await fetch(`${API_BASE_URL}/compare_websites`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          websites,
          category,
        }),
      });

      if (!response.ok) {
        let errorMsg = `Server responded with status: ${response.status}`;
        try {
          const errData = await response.json();
          if (errData && errData.error) {
            errorMsg = errData.error;
          }
        } catch (_) {}
        throw new Error(errorMsg);
      }

      const data = await response.json();
      
      // Get the current session ID
      const sessionId = sessionStorage.getItem('sessionId');
      
      // Save the response to localStorage for reuse by other components with session info
      localStorage.setItem('websiteComparisonData', JSON.stringify(data));
      localStorage.setItem('websiteComparisonTimestamp', Date.now().toString());
      localStorage.setItem('websiteComparisonSessionId', sessionId);
      console.log('API data cached in localStorage with session ID', sessionId);
      
      setResults(data);
      
      // Scroll to results
      const resultsElement = document.getElementById('results');
      if (resultsElement) {
        resultsElement.scrollIntoView({ behavior: 'smooth' });
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
      console.error('Error comparing websites:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle storage change event (if data is updated in another tab/component)
  const handleStorageChange = (e) => {
    if (e.key === 'websiteComparisonData' && e.newValue) {
      try {
        const newData = JSON.parse(e.newValue);
        const currentSessionId = sessionStorage.getItem('sessionId');
        const dataSessionId = localStorage.getItem('websiteComparisonSessionId');
        
        // Only update if the data is from the current session
        if (dataSessionId === currentSessionId) {
          setResults(newData);
        }
      } catch (err) {
        console.error('Error parsing stored data:', err);
      }
    }
  };
  
  // Add storage event listener when component mounts
  useEffect(() => {
    window.addEventListener('storage', handleStorageChange);
    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  // Function to clear cached data (for testing)
  const clearCache = () => {
    localStorage.removeItem('websiteComparisonData');
    localStorage.removeItem('websiteComparisonTimestamp');
    localStorage.removeItem('websiteComparisonSessionId');
    setResults(null);
  };

  return (
    <section id="analyze" className="py-20 bg-gradient-to-b from-indigo-950/30 to-black relative overflow-hidden">
      {/* Background elements */}
      <div className="absolute inset-0 overflow-hidden">
        {/* Radial gradient */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(79,70,229,0.1),transparent_70%)]"></div>
        
        {/* Circuit pattern overlay */}
        <div className="absolute inset-0 opacity-5">
          <div className="h-full w-full bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI2MCIgaGVpZ2h0PSI2MCIgdmlld0JveD0iMCAwIDYwIDYwIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmZmZmYiPjxwYXRoIGQ9Ik0zNiAxOGgtOHYtOGg4djh6bTIwIDIwaC04di04aDh2OHptLTEyLTEyaC04di04aDh2OHptLTIwIDBoLTh2LThoOHY4em0tMTIgMTJoLTh2LThoOHY4eiIvPjwvZz48L2c+PC9zdmc+')]"></div>
        </div>
        
        {/* Animated glowing elements */}
        <div className="absolute top-20 right-[10%] w-64 h-64 bg-fuchsia-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
        <div className="absolute bottom-10 left-[5%] w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse-slow animation-delay-2000"></div>
      </div>
      
      <div className="container mx-auto px-4 relative z-10">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-fuchsia-400">
              Analyze Websites
            </span>
          </h2>
          <p className="text-gray-400 max-w-2xl mx-auto">
            Compare multiple websites and get detailed design analysis with our AI-powered tool.
          </p>
          
          {/* Dev controls for clearing cache */}
          {process.env.NODE_ENV === 'development' && (
            <div className="mt-2">
              <button 
                onClick={clearCache} 
                className="text-xs bg-red-500/20 hover:bg-red-500/30 text-red-400 px-2 py-1 rounded"
              >
                Clear Cached Data (Dev Only)
              </button>
            </div>
          )}
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Form section */}
          <div>
            <WebsiteForm onSubmit={handleSubmit} loading={loading} />
            
            {/* Error message */}
            {error && (
              <div className="mt-6 p-4 bg-red-900/30 border border-red-800 rounded-lg text-red-400">
                <div className="flex items-center">
                  <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  {error}
                </div>
              </div>
            )}
            
            {/* How it works mini section */}
            <div className="mt-8 bg-gray-900/30 border border-gray-800 rounded-lg p-5">
              <h3 className="text-lg font-semibold mb-4 text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-fuchsia-400">
                How It Works
              </h3>
              <ol className="space-y-3 text-sm text-gray-300">
                <li className="flex">
                  <span className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full bg-indigo-900/50 text-cyan-400 text-xs font-bold mr-3">1</span>
                  <span>Enter the names and URLs of the websites you want to compare</span>
                </li>
                <li className="flex">
                  <span className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full bg-indigo-900/50 text-cyan-400 text-xs font-bold mr-3">2</span>
                  <span>Select the website category for more accurate analysis</span>
                </li>
                <li className="flex">
                  <span className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full bg-indigo-900/50 text-cyan-400 text-xs font-bold mr-3">3</span>
                  <span>Our AI captures screenshots and analyzes design elements</span>
                </li>
                <li className="flex">
                  <span className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full bg-indigo-900/50 text-cyan-400 text-xs font-bold mr-3">4</span>
                  <span>View detailed comparison results with quality scores</span>
                </li>
              </ol>
            </div>
          </div>
          
          {/* Results section */}
          <div id="results">
            {loading ? (
              <div className="h-full flex items-center justify-center backdrop-blur-sm bg-black/30 rounded-xl p-12 border border-gray-800">
                <div className="text-center">
                  <div className="inline-block mb-4">
                    <svg className="animate-spin h-10 w-10 text-cyan-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  </div>
                  <p className="text-lg font-medium text-cyan-400">Analyzing Websites</p>
                  <p className="text-sm text-gray-400 mt-2">Our AI is capturing and processing website data...</p>
                </div>
              </div>
            ) : results ? (
              <ResultsDisplay results={results} />
            ) : (
              <div className="h-full flex items-center justify-center backdrop-blur-sm bg-black/30 rounded-xl p-12 border border-gray-800">
                <div className="text-center max-w-md">
                  <div className="inline-block p-3 rounded-full bg-indigo-900/30 mb-4">
                    <svg className="w-8 h-8 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                    </svg>
                  </div>
                  <h3 className="text-xl font-semibold text-white mb-2">Ready to Analyze</h3>
                  <p className="text-gray-400">
                    Enter website details and click "Analyze Websites" to see AI-powered comparison results.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};

export default AnalyzeSection;
