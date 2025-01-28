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
        
        // Display results only once
        displayResults(data, resultDiv);
        
        // Show result container
        resultDiv.style.display = 'block';

    } catch (error) {
        resultDiv.innerHTML = `<div class="error">${error.message}</div>`;
        console.error('Error:', error);
    } finally {
        loadingDiv.style.display = 'none';
    }
}

function displayResults(data, resultDiv) {
    let resultsHtml = '<div class="analysis-container">';
    
    // Extracted Text Section
    resultsHtml += `
        <div class="extracted-text-section">
            <h2>Extracted Ingredients</h2>
            <div class="text-content">${data.extracted_text}</div>
        </div>
    `;

    // Analysis Results Section
    resultsHtml += '<div class="analysis-section">';
    resultsHtml += '<h2>Ingredients Analysis</h2>';
    
    const sortedIngredients = data.ingredients.sort((a, b) => {
        if (a.is_harmful === b.is_harmful) return b.confidence - a.confidence;
        return b.is_harmful - a.is_harmful;
    });

    // Summary Stats
    const harmfulCount = sortedIngredients.filter(i => i.is_harmful).length;
    const safetyScore = ((1 - harmfulCount/sortedIngredients.length) * 100).toFixed(1);
    
    // Display summary card
    resultsHtml += generateSummaryCard(safetyScore, harmfulCount, sortedIngredients.length);
    
    // Detailed Ingredients Analysis
    resultsHtml += '<div class="ingredients-analysis">';
    sortedIngredients.forEach(ingredient => {
        resultsHtml += generateIngredientCard(ingredient);
    });
    resultsHtml += '</div>';
    
    resultsHtml += '</div></div>';
    resultDiv.innerHTML = resultsHtml;
}

function generateIngredientCard(ingredient) {
    const statusClass = ingredient.is_harmful ? 'harmful' : 'safe';
    return `
        <div class="ingredient-card">
            <div class="ingredient-header ${statusClass}">
                <div class="ingredient-name">
                    <h3>${ingredient.ingredient}</h3>
                    <div class="confidence">Confidence: ${(ingredient.confidence * 100).toFixed(1)}%</div>
                </div>
                <span class="status-badge ${statusClass}">
                    ${ingredient.is_harmful ? '❌ Harmful' : '✅ Safe'}
                </span>
            </div>
            
            <div class="ingredient-content">
                <div class="main-info">
                    <div class="info-group">
                        <label>Category:</label>
                        <span>${ingredient.category || 'Unknown'}</span>
                    </div>
                    
                    ${ingredient.chemical_score ? `
                        <div class="info-group">
                            <label>Safety Score:</label>
                            <span>${ingredient.chemical_score}/10</span>
                        </div>
                    ` : ''}
                </div>

                ${ingredient.concerns && ingredient.concerns.length ? `
                    <div class="concerns-section warning-box">
                        <h4>⚠️ Concerns:</h4>
                        <ul>
                            ${ingredient.concerns.map(c => `<li>${c}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
                
                ${ingredient.alternatives && ingredient.alternatives.length ? `
                    <div class="alternatives-section info-box">
                        <h4>✨ Safe Alternatives:</h4>
                        <ul>
                            ${ingredient.alternatives.map(a => `<li>${a}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}

                ${ingredient.research_links ? `
                    <div class="research-section">
                        <h4>🔍 Learn More:</h4>
                        <div class="research-links">
                            ${Object.entries(ingredient.research_links).map(([name, url]) => `
                                <a href="${url}" target="_blank" class="research-link">
                                    ${name.toUpperCase()}
                                </a>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
                
                ${ingredient.note ? `
                    <div class="info-message">
                        ℹ️ ${ingredient.note}
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}

function displayDetailedResults(data, resultsDiv) {
    resultsDiv.innerHTML = '';
    
    if (data.extracted_text) {
        const textDiv = document.createElement('div');
        textDiv.className = 'extracted-text';
        textDiv.innerHTML = `<h3>Extracted Text:</h3><p>${data.extracted_text}</p>`;
        resultsDiv.appendChild(textDiv);
    }

    const ingredients = data.ingredients || [];
    if (ingredients.length > 0) {
        const analysisDiv = document.createElement('div');
        analysisDiv.className = 'analysis-results';
        analysisDiv.innerHTML = '<h3>Detailed Ingredients Analysis:</h3>';
        
        const list = document.createElement('ul');
        ingredients.forEach(ingredient => {
            const item = document.createElement('li');
            item.className = ingredient.is_harmful ? 'harmful' : 'safe';
            item.innerHTML = `
                <strong>${ingredient.ingredient}</strong>
                <span class="status">${ingredient.is_harmful ? '❌ Harmful' : '✅ Safe'}</span>
                <div class="details">
                    <p>Confidence: ${(ingredient.confidence * 100).toFixed(1)}%</p>
                    ${ingredient.category ? `<p>Category: ${ingredient.category}</p>` : ''}
                    ${ingredient.chemical_score ? `<p>Safety Score: ${ingredient.chemical_score}/10</p>` : ''}
                </div>
            `;
            list.appendChild(item);
        });
        
        analysisDiv.appendChild(list);
        resultsDiv.appendChild(analysisDiv);
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

// Add this function after displayResults
function generateSummaryCard(safetyScore, harmfulCount, totalCount) {
    const safeCount = totalCount - harmfulCount;
    const safetyStatus = safetyScore >= 70 ? 'safe' : 'warning';
    
    // Get commonly safe ingredients from our database
    const commonSafeIngredients = [
        {
            name: 'Vitamin E',
            benefits: ['Antioxidant', 'Skin conditioning']
        },
        {
            name: 'Aloe Vera',
            benefits: ['Soothing', 'Moisturizing']
        },
        {
            name: 'Glycerin',
            benefits: ['Hydrating', 'Moisturizing']
        },
        {
            name: 'Hyaluronic Acid',
            benefits: ['Hydrating', 'Anti-aging']
        },
        {
            name: 'Niacinamide',
            benefits: ['Brightening', 'Pore-reducing']
        }
    ];
    
    return `
        <div class="summary-card ${safetyStatus}">
            <div class="score-section">
                <div class="score-circle">
                    <svg viewBox="0 0 36 36" class="circular-chart ${safetyStatus}">
                        <path d="M18 2.0845
                            a 15.9155 15.9155 0 0 1 0 31.831
                            a 15.9155 15.9155 0 0 1 0 -31.831"
                            fill="none"
                            stroke-dasharray="${safetyScore}, 100"
                        />
                    </svg>
                    <div class="score-content">
                        <span class="score">${safetyScore}%</span>
                        <span class="label">Safety Score</span>
                    </div>
                </div>
                
                <div class="safe-ingredients-showcase">
                    <h4>Common Safe Ingredients</h4>
                    <div class="safe-ingredients-list">
                        ${commonSafeIngredients.map(ing => `
                            <div class="safe-ingredient-item">
                                <span class="safe-ingredient-name">✨ ${ing.name}</span>
                                <div class="safe-ingredient-benefits">
                                    ${ing.benefits.map(b => `<span class="benefit-tag">${b}</span>`).join('')}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
            
            <div class="summary-details">
                <h3>Product Safety Summary</h3>
                <div class="stats">
                    <div class="stat-item" onclick="showStatDetails('total', ${totalCount})">
                        <div class="stat-icon">📊</div>
                        <div class="stat-info">
                            <span class="stat-label">Total Ingredients</span>
                            <span class="stat-value">${totalCount}</span>
                        </div>
                        <div class="stat-hover">Click for details</div>
                    </div>
                    <div class="stat-item ${harmfulCount > 0 ? 'harmful' : ''}" 
                         onclick="showStatDetails('harmful', ${harmfulCount})">
                        <div class="stat-icon">⚠️</div>
                        <div class="stat-info">
                            <span class="stat-label">Harmful Ingredients</span>
                            <span class="stat-value">${harmfulCount}</span>
                        </div>
                        <div class="stat-hover">Click to see harmful ingredients</div>
                    </div>
                    <div class="stat-item safe" onclick="showStatDetails('safe', ${safeCount})">
                        <div class="stat-icon">✅</div>
                        <div class="stat-info">
                            <span class="stat-label">Safe Ingredients</span>
                            <span class="stat-value">${safeCount}</span>
                        </div>
                        <div class="stat-hover">Click to see safe ingredients</div>
                    </div>
                </div>
                
                <div class="recommendation">
                    <div class="recommendation-icon">${getRecommendationIcon(safetyScore)}</div>
                    <div class="recommendation-text">
                        ${getRecommendation(safetyScore, harmfulCount)}
                    </div>
                </div>
                
                <div class="action-buttons">
                    <button onclick="showDetailedAnalysis()" class="action-btn">
                        View Detailed Analysis
                    </button>
                    <button onclick="exportReport()" class="action-btn secondary">
                        Export Report
                    </button>
                </div>
            </div>
        </div>
    `;
}

function getRecommendation(safetyScore, harmfulCount) {
    if (safetyScore >= 90) {
        return '✅ This product appears to be very safe for use.';
    } else if (safetyScore >= 70) {
        return '✓ This product is generally safe, but contains some ingredients to be aware of.';
    } else if (safetyScore >= 50) {
        return '⚠️ Exercise caution with this product. Consider alternatives for sensitive skin.';
    } else {
        return '❌ This product contains several concerning ingredients. Consider safer alternatives.';
    }
}

function getRecommendationIcon(safetyScore) {
    if (safetyScore >= 90) return '🌟';
    if (safetyScore >= 70) return '✅';
    if (safetyScore >= 50) return '⚠️';
    return '❌';
}

function showStatDetails(type, count) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    
    let content = '';
    switch(type) {
        case 'harmful':
            content = generateHarmfulList();
            break;
        case 'safe':
            content = generateSafeList();
            break;
        case 'total':
            content = generateTotalList();
            break;
    }
    
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close-btn" onclick="this.parentElement.parentElement.remove()">&times;</span>
            <h2>${type.charAt(0).toUpperCase() + type.slice(1)} Ingredients</h2>
            ${content}
        </div>
    `;
    
    document.body.appendChild(modal);
}

function showDetailedAnalysis() {
    document.querySelector('.ingredients-analysis').scrollIntoView({ 
        behavior: 'smooth' 
    });
}

function exportReport() {
    // Implementation for exporting report
    alert('Report export feature coming soon!');
}
