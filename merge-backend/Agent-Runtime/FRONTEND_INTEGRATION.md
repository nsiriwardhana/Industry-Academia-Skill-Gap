# Frontend Integration - XAI Friendly Explanations

## Quick Start

### API Endpoint
```
GET http://localhost:8003/runtime/predict-explain
```

### Query Parameters
- `candidate_id` (required): Candidate ID
- `role_key` (required): Target role (e.g., "ai_ml_engineer")
- `top_k` (optional): Number of factors to return (default: 5, max: 10)

### Example Request
```javascript
const response = await fetch(
  `http://localhost:8003/runtime/predict-explain?` +
  `candidate_id=${candidateId}&` +
  `role_key=${roleKey}&` +
  `top_k=5`
);
const data = await response.json();
```

## Response Structure

```typescript
interface FriendlyXAIResponse {
  enabled: boolean;
  reason?: string;  // If disabled
  predicted_skill_gap_index: number;  // 0-1 (higher = more gap)
  predicted_readiness: number;  // 0-1 (higher = better)
  top_increasing_factors: FeatureImpact[];  // Bad for candidate
  top_reducing_factors: FeatureImpact[];  // Good for candidate
  summary_text: string;
  base_value: number;
  notes: string[];
}

interface FeatureImpact {
  feature: string;  // "Role-Skill Match Coverage"
  value: number | null;  // 0.12 (original value)
  impact: number;  // 0.08 (SHAP value)
  message: string;  // "You have limited coverage..."
}
```

## Display Examples

### React Component

```jsx
function XAIExplanation({ candidateId, roleKey }) {
  const [xai, setXai] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchXAI();
  }, [candidateId, roleKey]);

  async function fetchXAI() {
    setLoading(true);
    try {
      const response = await fetch(
        `http://localhost:8003/runtime/predict-explain?` +
        `candidate_id=${candidateId}&role_key=${roleKey}&top_k=5`
      );
      const data = await response.json();
      setXai(data);
    } catch (error) {
      console.error('XAI fetch failed:', error);
    }
    setLoading(false);
  }

  if (loading) return <div>Loading explanations...</div>;
  if (!xai?.enabled) return <div>Explanations not available</div>;

  return (
    <div className="xai-container">
      {/* Prediction */}
      <div className="prediction-card">
        <h3>ML Prediction</h3>
        <div className="readiness-score">
          {(xai.predicted_readiness * 100).toFixed(1)}% Readiness
        </div>
        <p className="summary">{xai.summary_text}</p>
      </div>

      {/* Strengths */}
      <div className="strengths-section">
        <h4>✅ Your Strengths</h4>
        {xai.top_reducing_factors.map((factor, idx) => (
          <div key={idx} className="factor-card positive">
            <div className="factor-name">{factor.feature}</div>
            <div className="factor-message">{factor.message}</div>
            {factor.value !== null && (
              <div className="factor-value">Value: {factor.value}</div>
            )}
            <div className="factor-impact">
              Impact: {(factor.impact * 100).toFixed(1)}%
            </div>
          </div>
        ))}
      </div>

      {/* Areas to Improve */}
      <div className="improvements-section">
        <h4>⚠️ Areas to Improve</h4>
        {xai.top_increasing_factors.map((factor, idx) => (
          <div key={idx} className="factor-card negative">
            <div className="factor-name">{factor.feature}</div>
            <div className="factor-message">{factor.message}</div>
            {factor.value !== null && (
              <div className="factor-value">Value: {factor.value}</div>
            )}
            <div className="factor-impact">
              Impact: +{(factor.impact * 100).toFixed(1)}%
            </div>
          </div>
        ))}
      </div>

      {/* Notes */}
      {xai.notes && (
        <div className="notes-section">
          {xai.notes.map((note, idx) => (
            <p key={idx} className="note">{note}</p>
          ))}
        </div>
      )}
    </div>
  );
}
```

### CSS Styling

```css
.xai-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.prediction-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 30px;
  border-radius: 12px;
  margin-bottom: 30px;
  text-align: center;
}

.readiness-score {
  font-size: 48px;
  font-weight: bold;
  margin: 15px 0;
}

.summary {
  font-size: 18px;
  opacity: 0.95;
  margin-top: 15px;
}

.strengths-section,
.improvements-section {
  margin-bottom: 30px;
}

.strengths-section h4 {
  color: #10b981;
  font-size: 20px;
  margin-bottom: 15px;
}

.improvements-section h4 {
  color: #ef4444;
  font-size: 20px;
  margin-bottom: 15px;
}

.factor-card {
  background: white;
  border-left: 4px solid;
  padding: 20px;
  margin-bottom: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.factor-card.positive {
  border-left-color: #10b981;
  background: linear-gradient(to right, #ecfdf5, white);
}

.factor-card.negative {
  border-left-color: #ef4444;
  background: linear-gradient(to right, #fef2f2, white);
}

.factor-name {
  font-weight: 600;
  font-size: 16px;
  color: #1f2937;
  margin-bottom: 8px;
}

.factor-message {
  font-size: 14px;
  color: #4b5563;
  margin-bottom: 10px;
  line-height: 1.5;
}

.factor-value {
  font-size: 13px;
  color: #6b7280;
  font-family: 'Courier New', monospace;
}

.factor-impact {
  font-size: 13px;
  font-weight: 600;
  color: #9ca3af;
  margin-top: 5px;
}

.notes-section {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 15px;
  margin-top: 30px;
}

.note {
  font-size: 13px;
  color: #6b7280;
  margin: 5px 0;
  font-style: italic;
}
```

### Vue Component

```vue
<template>
  <div class="xai-container">
    <div v-if="loading">Loading explanations...</div>
    <div v-else-if="!xai?.enabled">Explanations not available</div>
    <div v-else>
      <!-- Prediction -->
      <div class="prediction-card">
        <h3>ML Prediction</h3>
        <div class="readiness-score">
          {{ (xai.predicted_readiness * 100).toFixed(1) }}% Readiness
        </div>
        <p class="summary">{{ xai.summary_text }}</p>
      </div>

      <!-- Strengths -->
      <div class="strengths-section">
        <h4>✅ Your Strengths</h4>
        <div
          v-for="(factor, idx) in xai.top_reducing_factors"
          :key="idx"
          class="factor-card positive"
        >
          <div class="factor-name">{{ factor.feature }}</div>
          <div class="factor-message">{{ factor.message }}</div>
          <div v-if="factor.value !== null" class="factor-value">
            Value: {{ factor.value }}
          </div>
        </div>
      </div>

      <!-- Areas to Improve -->
      <div class="improvements-section">
        <h4>⚠️ Areas to Improve</h4>
        <div
          v-for="(factor, idx) in xai.top_increasing_factors"
          :key="idx"
          class="factor-card negative"
        >
          <div class="factor-name">{{ factor.feature }}</div>
          <div class="factor-message">{{ factor.message }}</div>
          <div v-if="factor.value !== null" class="factor-value">
            Value: {{ factor.value }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    candidateId: String,
    roleKey: String,
  },
  data() {
    return {
      xai: null,
      loading: true,
    };
  },
  mounted() {
    this.fetchXAI();
  },
  methods: {
    async fetchXAI() {
      this.loading = true;
      try {
        const response = await fetch(
          `http://localhost:8003/runtime/predict-explain?` +
          `candidate_id=${this.candidateId}&` +
          `role_key=${this.roleKey}&top_k=5`
        );
        this.xai = await response.json();
      } catch (error) {
        console.error('XAI fetch failed:', error);
      }
      this.loading = false;
    },
  },
};
</script>
```

## Integration with Existing Agent Run

If you're already calling `/agent/run?include_xai=true`:

```javascript
// Agent run response includes XAI
const response = await fetch(
  `http://localhost:8003/agent/run?` +
  `role_key=${roleKey}&top_k=25&include_xai=true`,
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cvData),
  }
);

const result = await response.json();

// Extract XAI data
const xai = result.xai;

if (xai?.shap_level?.enabled) {
  const shapData = xai.shap_level;
  
  // Display predictions
  console.log(`Readiness: ${shapData.predicted_readiness}`);
  console.log(`Summary: ${shapData.summary_text}`);
  
  // Display factors
  shapData.top_reducing_factors.forEach(factor => {
    console.log(`✅ ${factor.message}`);
  });
  
  shapData.top_increasing_factors.forEach(factor => {
    console.log(`⚠️ ${factor.message}`);
  });
}
```

## Common Patterns

### 1. Simple List View

```jsx
<ul>
  {xai.top_increasing_factors.map((f, i) => (
    <li key={i}>⚠️ {f.message}</li>
  ))}
</ul>
```

### 2. Progress Bars

```jsx
{xai.top_increasing_factors.map((f, i) => (
  <div key={i}>
    <span>{f.feature}</span>
    <div className="progress-bar">
      <div style={{width: `${Math.abs(f.impact) * 100}%`}} />
    </div>
    <p>{f.message}</p>
  </div>
))}
```

### 3. Accordion View

```jsx
<Accordion>
  <AccordionItem title="Areas to Improve">
    {xai.top_increasing_factors.map((f, i) => (
      <Card key={i}>
        <h5>{f.feature}</h5>
        <p>{f.message}</p>
      </Card>
    ))}
  </AccordionItem>
  
  <AccordionItem title="Your Strengths">
    {xai.top_reducing_factors.map((f, i) => (
      <Card key={i}>
        <h5>{f.feature}</h5>
        <p>{f.message}</p>
      </Card>
    ))}
  </AccordionItem>
</Accordion>
```

### 4. Tooltip View

```jsx
{xai.top_increasing_factors.map((f, i) => (
  <Tooltip key={i} content={f.message}>
    <Badge variant="warning">{f.feature}</Badge>
  </Tooltip>
))}
```

## Best Practices

1. **Show summary first**: Users want quick overview
2. **Strengths before weaknesses**: Positive reinforcement
3. **Limit to 5 factors**: Avoid overwhelming users
4. **Use icons**: ✅ for strengths, ⚠️ for improvements
5. **Color coding**: Green for good, red for bad
6. **Mobile friendly**: Stack cards vertically on small screens
7. **Loading states**: Show spinner while fetching
8. **Error handling**: Graceful fallback if API fails

## Accessibility

```jsx
<div role="region" aria-label="Skill gap explanation">
  <h3 id="xai-heading">Why This Prediction?</h3>
  
  <section aria-labelledby="strengths-heading">
    <h4 id="strengths-heading">Your Strengths</h4>
    {/* ... */}
  </section>
  
  <section aria-labelledby="improvements-heading">
    <h4 id="improvements-heading">Areas to Improve</h4>
    {/* ... */}
  </section>
</div>
```

## Testing

```javascript
// Mock data for testing
const mockXAI = {
  enabled: true,
  predicted_readiness: 0.544,
  predicted_skill_gap_index: 0.456,
  summary_text: "Main gap contributors: role-skill match coverage. Key strengths: number of projects.",
  top_reducing_factors: [
    {
      feature: "Number of Projects",
      value: 5.0,
      impact: -0.05,
      message: "Your project portfolio demonstrates practical capability."
    }
  ],
  top_increasing_factors: [
    {
      feature: "Role-Skill Match Coverage",
      value: 0.12,
      impact: 0.08,
      message: "You have limited coverage of the skills required for this role."
    }
  ],
  base_value: 0.50,
  notes: ["Graph-based readiness is the authoritative score; ML is an estimate."]
};
```

## Troubleshooting

**Empty response?**
- Check Agent-Runtime is running on port 8003
- Verify candidate exists in Neo4j
- Check browser console for CORS errors

**Still seeing feature_5?**
- Server may not be restarted after update
- Check API version: `/runtime/predict-explain` (new) vs `/runtime/predict-explain-legacy` (old)

**No factors displayed?**
- Check `xai.enabled` is `true`
- Verify model is loaded (check server logs)
- Ensure candidate has data in Neo4j

---

Ready to integrate? Copy the React component above and customize to your design!
