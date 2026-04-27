<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div class="card budget-card">
      <div class="budget-label">
        <span class="budget-key">{{ t('restocking.budget') }}</span>
        <span class="budget-value">{{ formatCurrency(budget) }}</span>
      </div>
      <input
        type="range"
        min="5000"
        max="250000"
        step="1000"
        v-model.number="budget"
        class="budget-slider"
      />
      <div class="slider-labels">
        <span>{{ formatCurrency(5000) }}</span>
        <span>{{ formatCurrency(250000) }}</span>
      </div>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.totalCost') }}</div>
          <div class="stat-value">{{ formatCurrency(recommendations.total_cost) }}</div>
        </div>
        <div class="stat-card" :class="recommendations.remaining_budget >= 0 ? 'success' : 'danger'">
          <div class="stat-label">{{ t('restocking.remaining') }}</div>
          <div class="stat-value">{{ formatCurrency(recommendations.remaining_budget) }}</div>
        </div>
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.leadTime') }}</div>
          <div class="stat-value">
            {{ recommendations.lead_time_days }}
            <span class="stat-unit">{{ t('restocking.days') }}</span>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }}</h3>
        </div>
        <div class="table-container">
          <table v-if="recommendations.items.length > 0">
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.name') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th>{{ t('restocking.table.onHand') }}</th>
                <th>{{ t('restocking.table.forecast') }}</th>
                <th>{{ t('restocking.table.shortfall') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.qty') }}</th>
                <th>{{ t('restocking.table.lineCost') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in recommendations.items" :key="item.item_sku">
                <td><strong>{{ item.item_sku }}</strong></td>
                <td>{{ item.item_name }}</td>
                <td>
                  <span :class="['badge', item.trend]">{{ item.trend }}</span>
                </td>
                <td>{{ item.quantity_on_hand }}</td>
                <td>{{ item.forecasted_demand }}</td>
                <td class="shortfall-cell">{{ item.shortfall }}</td>
                <td>{{ formatCurrency(item.unit_cost) }}</td>
                <td><strong>{{ item.recommended_qty }}</strong></td>
                <td><strong>{{ formatCurrency(item.line_cost) }}</strong></td>
              </tr>
            </tbody>
          </table>
          <div v-else class="no-items">{{ t('restocking.noItems') }}</div>
        </div>
      </div>

      <div class="action-bar">
        <button
          class="btn-primary"
          :disabled="!canSubmit"
          @click="placeOrder"
        >
          {{ submitting ? t('restocking.placingOrder') : t('restocking.placeOrder') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrency } from '../utils/currency'

export default {
  name: 'Restocking',
  setup() {
    const { t } = useI18n()
    const router = useRouter()
    const budget = ref(50000)
    const recommendations = ref({ items: [], total_cost: 0, remaining_budget: 0, lead_time_days: 0 })
    const loading = ref(true)
    const submitting = ref(false)
    const error = ref(null)

    const canSubmit = computed(() => recommendations.value.items.length > 0 && !submitting.value)

    const loadRecommendations = async () => {
      error.value = null
      loading.value = true
      try {
        const data = await api.getRestockRecommendations(budget.value)
        recommendations.value = data
      } catch (err) {
        error.value = 'Failed to load recommendations: ' + err.message
      } finally {
        loading.value = false
      }
    }

    let debounceTimer = null
    watch(budget, () => {
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(loadRecommendations, 300)
    })

    const placeOrder = async () => {
      if (!canSubmit.value) return
      submitting.value = true
      try {
        const items = recommendations.value.items.map(item => ({
          item_sku: item.item_sku,
          item_name: item.item_name,
          quantity: item.recommended_qty,
          unit_cost: item.unit_cost,
          lead_time_days: item.lead_time_days
        }))
        await api.createRestockOrder({ budget: budget.value, items })
        router.push('/orders')
      } catch (err) {
        error.value = 'Failed to place order: ' + err.message
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadRecommendations)

    return {
      t,
      budget,
      recommendations,
      loading,
      submitting,
      error,
      canSubmit,
      placeOrder,
      formatCurrency
    }
  }
}
</script>

<style scoped>
.budget-card {
  margin-bottom: 1.5rem;
}

.budget-label {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  margin-bottom: 1rem;
}

.budget-key {
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.budget-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.budget-slider {
  width: 100%;
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  border-radius: 3px;
  background: #e2e8f0;
  outline: none;
  cursor: pointer;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #0f172a;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  transition: background 0.2s;
}

.budget-slider::-webkit-slider-thumb:hover {
  background: #1e293b;
}

.budget-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #0f172a;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.budget-slider::-moz-range-track {
  height: 6px;
  border-radius: 3px;
  background: #e2e8f0;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #94a3b8;
}

.stat-unit {
  font-size: 1rem;
  font-weight: 500;
  color: #64748b;
}

.shortfall-cell {
  color: #dc2626;
  font-weight: 600;
}

.no-items {
  text-align: center;
  padding: 2.5rem;
  color: #64748b;
  font-size: 0.938rem;
}

.action-bar {
  display: flex;
  justify-content: flex-end;
  padding: 1rem 0;
}

.btn-primary {
  background: #0f172a;
  color: white;
  border: none;
  padding: 0.75rem 2rem;
  border-radius: 8px;
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, opacity 0.2s;
  letter-spacing: 0.01em;
}

.btn-primary:hover:not(:disabled) {
  background: #1e293b;
}

.btn-primary:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
