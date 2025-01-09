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
        const response = await fetch('http://127.0.0.1:5000/analyze-ingredients', {
            method: 'POST',
            body: formData,
            mode: 'cors'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Response data:', data); // For debugging
        
        if (data.error) {
            resultsDiv.innerHTML = `<div class="error">${data.error}</div>`;
            return;
        }
        
        const harmfulIngredientsHtml = data.harmful_ingredients && data.harmful_ingredients.length > 0 
            ? `
                <h3>Harmful Ingredients Found:</h3>
                <ul>
                    ${data.harmful_ingredients.map(item => 
                        `<li>${item.ingredient} (Score: ${item.score}) - ${item.reason || 'No specific concerns listed'}</li>`
                    ).join('')}
                </ul>
            `
            : '<h3 class="safe">No harmful ingredients detected!</h3>';

        const safeIngredientsHtml = data.safe_ingredients && data.safe_ingredients.length > 0
            ? `
                <h3>Safe Ingredients:</h3>
                <ul>
                    ${data.safe_ingredients.map(item => 
                        `<li>${item.ingredient} (Score: ${item.score})</li>`
                    ).join('')}
                </ul>
            `
            : '';
        
        resultsDiv.innerHTML = `
            <div class="ingredients-text">
                <h3>Extracted Ingredients:</h3>
                <p>${data.ingredients_text || 'No ingredients text found'}</p>
            </div>
            <div class="analysis ${data.is_safe ? 'safe' : 'unsafe'}">
                <h3>Safety Score: ${data.safety_score}/100</h3>
                ${harmfulIngredientsHtml}
                ${safeIngredientsHtml}
            </div>
        `;
    } catch (error) {
        console.error('Error:', error); // For debugging
        resultsDiv.innerHTML = `<div class="error">Error: ${error.message}</div>`;
    }
}
