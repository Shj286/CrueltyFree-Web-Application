import React, { useState } from 'react';
import './App.css';

async function analyzeProduct() {
    const fileInput = document.getElementById('productImage');
    const resultsDiv = document.getElementById('results');
    
    if (!fileInput.files[0]) {
        alert('Please select an image first');
        return;
    }
    
    resultsDiv.innerHTML = 'Analyzing...';
    
    const formData = new FormData();
    formData.append('image', fileInput.files[0]);
    
    try {
        const response = await fetch('http://localhost:5000/analyze-ingredients', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.error) {
            resultsDiv.innerHTML = `<div class="error">${data.error}</div>`;
            return;
        }
        
        const harmfulIngredientsHtml = data.harmful_ingredients.length > 0 
            ? `
                <h3>Harmful Ingredients Found:</h3>
                <ul>
                    ${data.harmful_ingredients.map(item => 
                        `<li>${item.ingredient} (${item.category})</li>`
                    ).join('')}
                </ul>
            `
            : '<h3 class="safe">No harmful ingredients detected!</h3>';
        
        resultsDiv.innerHTML = `
            <div class="ingredients-text">
                <h3>Extracted Ingredients:</h3>
                <p>${data.ingredients_text}</p>
            </div>
            <div class="analysis ${data.is_safe ? 'safe' : 'unsafe'}">
                ${harmfulIngredientsHtml}
            </div>
        `;
    } catch (error) {
        resultsDiv.innerHTML = `<div class="error">Error: ${error.message}</div>`;
    }
}

function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState('');

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleSubmit = async () => {
    if (!file) {
      alert('Please upload an image.');
      return;
    }

    const formData = new FormData();
    formData.append('image', file);

    try {
      const response = await fetch('http://127.0.0.1:5000/predict', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      if (data.prediction) {
        setResult(`Prediction: ${data.prediction}`);
      } else {
        alert('Error: ' + data.error);
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Failed to get prediction.');
    }
  };

  return (
    <div className="App">
      <h1>Cruelty-Free Product Detector</h1>
      <input type="file" onChange={handleFileChange} />
      <button onClick={handleSubmit}>Upload and Predict</button>
      {result && <p>{result}</p>}
    </div>
  );
}

export default App;
