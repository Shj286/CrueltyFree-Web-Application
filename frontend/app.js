// Add connection management
const BACKEND_URL = window.location.origin;
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1 second

async function checkServerConnection() {
    try {
        const response = await fetch(`${BACKEND_URL}/test-connection`);
        return response.ok;
    } catch (error) {
        console.error('Server connection check failed:', error);
        return false;
    }
}

async function retryOperation(operation, retries = MAX_RETRIES) {
    for (let i = 0; i < retries; i++) {
        try {
            const isConnected = await checkServerConnection();
            if (!isConnected) {
                throw new Error('Server is not responding');
            }
            return await operation();
        } catch (error) {
            if (i === retries - 1) throw error;
            await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
            console.log(`Retrying operation... Attempt ${i + 2}/${retries}`);
        }
    }
}

async function analyzeProduct() {
    const fileInput = document.getElementById('productImage');
    const resultsDiv = document.getElementById('results');
    const loadingDiv = document.getElementById('loading');
    
    if (!fileInput.files[0]) {
        showNotification('Please select an image of product ingredients', 'error');
        return;
    }
    
    // Check file type
    const file = fileInput.files[0];
    const validTypes = ['image/jpeg', 'image/png', 'image/jpg'];
    if (!validTypes.includes(file.type)) {
        showNotification('Please upload a valid image file (JPEG, PNG) of product ingredients', 'error');
        return;
    }
    
    // Check file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
        showNotification('Image size should be less than 5MB', 'error');
        return;
    }
    
    try {
        loadingDiv.style.display = 'block';
        resultsDiv.innerHTML = '';

        const analyzeOperation = async () => {
            const formData = new FormData();
            formData.append('image', file);
            
            const response = await fetch(`${BACKEND_URL}/analyze-ingredients`, {
                method: 'POST',
                body: formData,
                mode: 'cors'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        };

        const data = await retryOperation(analyzeOperation);
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Calculate safety percentage
        const safetyPercentage = (data.safe_ingredients.length / data.total_ingredients) * 100;
        
        const harmfulIngredientsHtml = data.detailed_harmful && data.detailed_harmful.length > 0 
            ? `
                <div class="harmful-ingredients">
                    <h3>⚠️ Harmful Ingredients Found:</h3>
                    <ul>
                        ${data.detailed_harmful.map(item => `
                            <li class="harmful-item">
                                <strong>${item.name}</strong>
                                <div class="harm-details">
                                    <span class="score">Risk Score: ${item.score}/10</span>
                                    ${item.concerns.length ? `
                                        <div class="concerns">
                                            <strong>Concerns:</strong>
                                            <ul>
                                                ${item.concerns.map(concern => `<li>${concern}</li>`).join('')}
                                            </ul>
                                        </div>
                                    ` : ''}
                                    ${item.alternatives.length ? `
                                        <div class="alternatives">
                                            <strong>Safer Alternatives:</strong>
                                            <ul>
                                                ${item.alternatives.map(alt => `<li>${alt}</li>`).join('')}
                                            </ul>
                                        </div>
                                    ` : ''}
                                </div>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            `
            : '<div class="safe-notice"><h3>✅ No harmful ingredients detected!</h3></div>';

        const safeIngredientsHtml = data.safe_ingredients && data.safe_ingredients.length > 0
            ? `
                <div class="safe-ingredients">
                    <h3>✅ Safe Ingredients:</h3>
                    <ul>
                        ${data.safe_ingredients.map(item => `<li>${item}</li>`).join('')}
                    </ul>
                </div>
            `
            : '';
        
        resultsDiv.innerHTML = `
            <div class="analysis-results ${safetyPercentage >= 75 ? 'safe' : 'unsafe'}">
                <div class="safety-score">
                    <h2>Safety Analysis</h2>
                    <div class="score-circle">
                        <span class="percentage">${Math.round(safetyPercentage)}%</span>
                        <span class="safe-text">Safe</span>
                    </div>
                </div>
                <div class="ingredients-breakdown">
                    <div class="total-ingredients">
                        <h3>Total Ingredients: ${data.total_ingredients}</h3>
                    </div>
                    ${harmfulIngredientsHtml}
                    ${safeIngredientsHtml}
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Error:', error);
        resultsDiv.innerHTML = `
            <div class="error-message">
                <h3>⚠️ Error</h3>
                <p>${error.message}</p>
                <div class="error-help">
                    <h4>Image Requirements:</h4>
                    <ul>
                        <li>Must be a clear image of product ingredients list</li>
                        <li>Text should be clearly readable</li>
                        <li>Avoid general product photos or other image types</li>
                        <li>Supported formats: JPG, PNG</li>
                        <li>Maximum size: 5MB</li>
                    </ul>
                    <p>Example of a good image: A clear, close-up photo of the ingredients list on the product packaging.</p>
                </div>
            </div>
        `;
        showNotification('Failed to analyze ingredients. Please check image requirements.', 'error');
    } finally {
        loadingDiv.style.display = 'none';
    }
}

// Check server connection on page load
window.addEventListener('load', async () => {
    const isConnected = await checkServerConnection();
    if (!isConnected) {
        showNotification('Warning: Server connection issues. Please ensure the server is running.', 'warning');
    }
});
