// ========================================
// StockFolio - Frontend JavaScript
// ========================================

document.addEventListener('DOMContentLoaded', function () {
    // --- Add Asset Modal ---
    setupAddAssetForm();

    // --- Add Transaction Form ---
    setupAddTransactionForm();

    // --- Transaction type toggle ---
    setupTransactionTypeToggle();

    // --- Set default date for purchase date input ---
    const purchaseDateInput = document.getElementById('purchaseDate');
    if (purchaseDateInput && !purchaseDateInput.value) {
        purchaseDateInput.value = new Date().toISOString().split('T')[0];
    }
});


// ========================================
// Modal Management
// ========================================

function openAddAssetModal() {
    const modal = document.getElementById('addAssetModal');
    if (modal) {
        modal.style.display = 'flex';
        const symbolInput = document.getElementById('assetSymbol');
        if (symbolInput) symbolInput.focus();
    }
}

function closeAddAssetModal() {
    const modal = document.getElementById('addAssetModal');
    if (modal) {
        modal.style.display = 'none';
        // Reset form
        const form = document.getElementById('addAssetForm');
        if (form) form.reset();
        hideElement('symbolLookupResult');
        hideElement('addAssetError');
    }
}

// Close modal on Escape key
document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
        closeAddAssetModal();
    }
});


// ========================================
// Symbol Lookup
// ========================================

async function lookupSymbol() {
    const symbolInput = document.getElementById('assetSymbol');
    const resultDiv = document.getElementById('symbolLookupResult');
    const nameInput = document.getElementById('assetName');
    const exchangeInput = document.getElementById('assetExchange');

    const symbol = symbolInput.value.trim().toUpperCase();
    if (!symbol) {
        showLookupError('Please enter a symbol');
        return;
    }

    resultDiv.style.display = 'block';
    resultDiv.className = 'lookup-result';
    resultDiv.textContent = 'Looking up ' + symbol + '...';

    try {
        const response = await fetch('/api/stock/' + encodeURIComponent(symbol));
        const data = await response.json();

        if (data.success && data.current_price > 0) {
            resultDiv.className = 'lookup-result';
            resultDiv.innerHTML =
                '<strong>' + data.name + '</strong> &mdash; ' +
                data.exchange + ' &mdash; $' + data.current_price.toFixed(2) + ' ' + data.currency;

            // Auto-fill name and exchange
            if (nameInput) nameInput.value = data.name;
            if (exchangeInput) exchangeInput.value = data.exchange;
        } else {
            showLookupError('Symbol not found or no data available for "' + symbol + '"');
        }
    } catch (err) {
        showLookupError('Lookup failed: ' + err.message);
    }
}

function showLookupError(message) {
    const resultDiv = document.getElementById('symbolLookupResult');
    if (resultDiv) {
        resultDiv.style.display = 'block';
        resultDiv.className = 'lookup-result lookup-error';
        resultDiv.textContent = message;
    }
}


// ========================================
// Add Asset Form
// ========================================

function setupAddAssetForm() {
    const form = document.getElementById('addAssetForm');
    if (!form) return;

    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        hideElement('addAssetError');

        const symbol = document.getElementById('assetSymbol').value.trim().toUpperCase();
        const name = document.getElementById('assetName').value.trim();
        const exchange = document.getElementById('assetExchange').value.trim();
        const assetType = document.getElementById('assetType').value;

        if (!symbol) {
            showFormError('addAssetError', 'Symbol is required');
            return;
        }

        try {
            const response = await fetch('/api/assets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol: symbol,
                    name: name,
                    exchange: exchange,
                    asset_type: assetType
                })
            });

            const data = await response.json();

            if (data.success) {
                // Reload page to show new asset
                window.location.reload();
            } else {
                showFormError('addAssetError', data.error || 'Failed to add asset');
            }
        } catch (err) {
            showFormError('addAssetError', 'Error: ' + err.message);
        }
    });
}


// ========================================
// Transaction Type Toggle
// ========================================

function setupTransactionTypeToggle() {
    const typeSelect = document.getElementById('transactionType');
    if (!typeSelect) return;

    typeSelect.addEventListener('change', function () {
        toggleTransactionFields(this.value);
    });

    // Initialize on load
    toggleTransactionFields(typeSelect.value);
}

function toggleTransactionFields(txnType) {
    const purchaseFields = document.querySelectorAll('.purchase-field');
    const dividendFields = document.querySelectorAll('.dividend-field');

    if (txnType === 'dividend') {
        purchaseFields.forEach(function (el) { el.style.display = 'none'; });
        dividendFields.forEach(function (el) { el.style.display = ''; });
    } else {
        purchaseFields.forEach(function (el) { el.style.display = ''; });
        dividendFields.forEach(function (el) { el.style.display = 'none'; });
    }
}


// ========================================
// Add Transaction Form
// ========================================

function setupAddTransactionForm() {
    const form = document.getElementById('addTransactionForm');
    if (!form) return;

    const assetId = form.dataset.assetId;

    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        hideElement('addTransactionError');

        const transactionType = document.getElementById('transactionType').value;
        const purchaseDate = document.getElementById('purchaseDate').value;
        const notes = document.getElementById('purchaseNotes').value.trim();

        if (!purchaseDate) {
            showFormError('addTransactionError', 'Date is required');
            return;
        }

        var body = {
            transaction_type: transactionType,
            purchase_date: purchaseDate,
            notes: notes
        };

        if (transactionType === 'purchase') {
            var pricePerUnit = parseFloat(document.getElementById('purchasePrice').value);
            var quantity = parseFloat(document.getElementById('purchaseQuantity').value);
            var fees = parseFloat(document.getElementById('purchaseFees').value) || 0;

            if (!pricePerUnit || pricePerUnit <= 0) {
                showFormError('addTransactionError', 'Price must be a positive number');
                return;
            }
            if (!quantity || quantity <= 0) {
                showFormError('addTransactionError', 'Quantity must be a positive number');
                return;
            }

            body.price_per_unit = pricePerUnit;
            body.quantity = quantity;
            body.fees = fees;
        } else {
            // Dividend
            var creditAmount = parseFloat(document.getElementById('dividendAmount').value);

            if (!creditAmount || creditAmount <= 0) {
                showFormError('addTransactionError', 'Dividend amount must be a positive number');
                return;
            }

            body.credit = creditAmount;
        }

        try {
            const response = await fetch('/api/assets/' + assetId + '/transactions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            const data = await response.json();

            if (data.success) {
                // Reload page to show new transaction
                window.location.reload();
            } else {
                showFormError('addTransactionError', data.error || 'Failed to add transaction');
            }
        } catch (err) {
            showFormError('addTransactionError', 'Error: ' + err.message);
        }
    });
}


// ========================================
// Delete Actions
// ========================================

async function deleteAsset(assetId, symbol) {
    if (!confirm('Are you sure you want to delete ' + symbol + ' and all its transactions? This cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch('/api/assets/' + assetId, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            window.location.href = '/dashboard';
        } else {
            alert('Failed to delete asset: ' + (data.error || 'Unknown error'));
        }
    } catch (err) {
        alert('Error deleting asset: ' + err.message);
    }
}

async function deleteTransaction(assetId, transactionId) {
    if (!confirm('Are you sure you want to delete this transaction? This cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch('/api/assets/' + assetId + '/transactions/' + transactionId, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            window.location.reload();
        } else {
            alert('Failed to delete transaction: ' + (data.error || 'Unknown error'));
        }
    } catch (err) {
        alert('Error deleting transaction: ' + err.message);
    }
}


// ========================================
// Utility Functions
// ========================================

function showFormError(elementId, message) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = message;
        el.style.display = 'block';
    }
}

function hideElement(elementId) {
    const el = document.getElementById(elementId);
    if (el) {
        el.style.display = 'none';
    }
}
