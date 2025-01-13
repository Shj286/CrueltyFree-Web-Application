// API endpoint configuration
const API_URL = window.location.origin;

async function analyzeProduct() {
    const fileInput = document.getElementById('imageInput');
    const resultDiv = document.getElementById('result');
    const loadingDiv = document.getElementById('loading');
    const file = fileInput.files[0];

    if (!file) {
        alert('Please select an image file');
        return;
    }

    try {
        // Show loading state
        loadingDiv.style.display = 'block';
        resultDiv.innerHTML = '';

        const formData = new FormData();
        formData.append('image', file);

        const response = await fetch(`${API_URL}/analyze-ingredients`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to analyze ingredients');
        }

        const data = await response.json();
        
        // Display results
        let resultsHtml = '<h2>Analysis Results:</h2>';
        resultsHtml += `<p>Extracted Text: ${data.extracted_text}</p>`;
        resultsHtml += '<h3>Ingredients Analysis:</h3>';
        
        // Sort ingredients by harmful status
        const sortedIngredients = data.ingredients.sort((a, b) => {
            if (a.is_harmful === b.is_harmful) {
                return b.confidence - a.confidence;
            }
            return b.is_harmful - a.is_harmful;
        });

        // Create results table
        resultsHtml += `
        <table class="results-table">
            <thead>
                <tr>
                    <th>Ingredient</th>
                    <th>Status</th>
                    <th>Confidence</th>
                    <th>Category</th>
                    <th>Chemical Score</th>
                </tr>
            </thead>
            <tbody>
        `;

        sortedIngredients.forEach(ingredient => {
            const statusClass = ingredient.is_harmful ? 'harmful' : 'safe';
            const confidencePercent = (ingredient.confidence * 100).toFixed(1);
            
            resultsHtml += `
                <tr class="${statusClass}">
                    <td>${ingredient.ingredient}</td>
                    <td>${ingredient.is_harmful ? 'Harmful' : 'Safe'}</td>
                    <td>${confidencePercent}%</td>
                    <td>${ingredient.category}</td>
                    <td>${ingredient.chemical_score.toFixed(1)}</td>
                </tr>
            `;
        });

        resultsHtml += '</tbody></table>';

        // Add summary
        const harmfulCount = sortedIngredients.filter(i => i.is_harmful).length;
        const totalCount = sortedIngredients.length;
        
        resultsHtml += `
        <div class="summary">
            <h3>Summary:</h3>
            <p>Found ${harmfulCount} harmful ingredients out of ${totalCount} total ingredients.</p>
            <p>Safety Rating: ${((1 - harmfulCount/totalCount) * 100).toFixed(1)}%</p>
        </div>`;

        resultDiv.innerHTML = resultsHtml;
    } catch (error) {
        resultDiv.innerHTML = `<div class="error">${error.message}</div>`;
    } finally {
        loadingDiv.style.display = 'none';
    }
}

// Event listener for file input
document.getElementById('imageInput').addEventListener('change', analyzeProduct);

// Test connection on page load
async function testConnection() {
    try {
        const response = await fetch(`${API_URL}/test-connection`);
        if (!response.ok) {
            throw new Error('Failed to connect to server');
        }
        console.log('Server connection successful');
    } catch (error) {
        console.error('Server connection failed:', error);
    }
}

testConnection();
