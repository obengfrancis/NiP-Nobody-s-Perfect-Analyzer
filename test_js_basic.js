// Basic Error Handling Only - No Advanced Patterns

async function fetchData(url) {
    try {
        const response = await fetch(url);
        
        if (response.status === 200) {
            return await response.json();
        } else {
            throw new Error(`HTTP ${response.status}`);
        }
    } catch (error) {
        console.error('Request failed:', error);
        throw error;
    }
}

function fetchWithPromise(url) {
    return fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .catch(error => {
            console.error('Error:', error);
            throw error;
        });
}

module.exports = { fetchData, fetchWithPromise };