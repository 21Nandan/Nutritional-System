import React, { useId, useState } from 'react';
import { gradeInfo, goalInfo, GRADE_BANDS } from '../scoring';
import { Chevron, Collapse } from './Expandable';

// The General Nutrition Grade: the same for everyone, against limits for the product's category.
// reason: the product's own explanation from the server when it has no grade (missing values, etc.).
// label: a product-specific label (see gradeLabelFor) in place of the band's general one.
export function GradeBadge({ grade, size = 'md', showLabel = true, reason = null, label = null }) {
  const info = { ...gradeInfo(grade) };
  if (label && info.graded) info.label = label;
  const why = (!info.graded && reason) || info.reason;
  return (
    <span className={`score-grade score-grade-${size}`}>
      <span
        className={`grade-badge ${info.className}`}
        role="img"
        aria-label={info.graded ? `Nutrition grade ${info.letter}: ${info.label}` : `Nutrition grade unavailable: ${why || info.label}`}
        title={why || info.label}
      >
        {info.letter}
      </span>
      {showLabel && <span className="score-grade-label">{info.label}</span>}
    </span>
  );
}

// Goal Match: personal fit for the visitor's goal, diet and allergens, out of 100.
export function GoalMatchMeter({ score, allergenConflict = false, size = 'md' }) {
  const info = goalInfo(score, { allergenConflict });
  return (
    <span className={`goal-meter goal-meter-${size} goal-${info.tone}`}>
      <span className="goal-meter-top">
        <span className="goal-meter-score">
          {info.available ? <>{info.score}<span className="goal-meter-max">/100</span></> : 'N/A'}
        </span>
        <span className="goal-meter-label">{info.label}</span>
      </span>
      <span
        className="goal-meter-track"
        role="meter"
        aria-label="Goal Match"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={info.available ? info.score : undefined}
        aria-valuetext={info.available ? `${info.score} out of 100, ${info.label}` : info.label}
      >
        <span className="goal-meter-fill" style={{ width: `${info.available ? Math.max(info.score, 2) : 0}%` }} />
      </span>
    </span>
  );
}

// Compact pair for cards and tables: grade on the left, Goal Match on the right.
// gradeNote: a label for grades from EATGOOD's own methods (not an official grade).
export function ScorePair({ grade, score, allergenConflict = false, gradeReason = null, gradeNote = null }) {
  const graded = gradeInfo(grade).graded;
  const ungradedReason = !graded && gradeReason;
  const note = graded && gradeNote;
  return (
    <div className="score-pair">
      <div className="score-pair-item">
        <span className="score-pair-heading">Nutrition grade</span>
        <GradeBadge grade={grade} size="sm" showLabel={false} reason={gradeReason} />
      </div>
      <div className="score-pair-item score-pair-goal">
        <span className="score-pair-heading">Goal Match</span>
        <GoalMatchMeter score={score} allergenConflict={allergenConflict} size="sm" />
      </div>
      {ungradedReason && <p className="score-pair-reason">{ungradedReason}</p>}
      {note && <p className="score-pair-reason">{note}</p>}
    </div>
  );
}

// "How are these scores worked out?" Uses the assessment's own numbers and the existing rules.
export function ScoreExplainer({ layer1, layer2 }) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const graded = gradeInfo(layer1?.grade).graded;
  return (
    <div className="score-explainer">
      <button type="button" className="score-explainer-toggle" aria-expanded={open} aria-controls={id} onClick={() => setOpen((v) => !v)}>
        <span>How are these scores worked out?</span>
        <Chevron open={open} />
      </button>
      <Collapse id={id} open={open}>
        <div className="score-explainer-body">
          <h4>Nutrition grade (the same for everyone)</h4>
          <p>
            The label is compared with limits for its category ({layer1?.reference_basis || 'per 100 g or 100 ml'}). Each nutrient over a limit
            adds penalty points (more if it is over double the limit), as does trans fat or very high energy; low sugar, sodium or saturated fat, fibre and protein add bonus points.
            If anything is over a limit, at most 3 bonus points count. Score = 50 − 7 × penalties + 8 × bonuses, kept between 10 and 100.
          </p>
          {graded && layer1?.raw_score != null && (
            <p className="score-explainer-calc">
              This product: 50 − 7 × {layer1.penalty_points} + 8 × {layer1.bonus_points} = {layer1.raw_score} → grade {layer1.grade}.
            </p>
          )}
          {!graded && <p className="score-explainer-calc">{gradeInfo(layer1?.grade).reason}</p>}
          <ul className="score-explainer-bands">
            {GRADE_BANDS.map((b) => <li key={b.grade}><strong>{b.grade}</strong> {b.grade === 'E' ? 'below 32' : `${b.min}+`}</li>)}
          </ul>
          <h4>Goal Match (personal to you)</h4>
          <p>
            Starts at 70. Rules for your goal ({layer2?.user_goal || 'Balanced Choices'}) add or subtract points, and saturated and trans fat always
            count (high values subtract, very low saturated fat adds). An allergen from your profile sets it to 0; a conflict with your diet caps it at 15. Kept between 1 and 100:
            75+ is a strong match, 50–74 moderate, below 50 poor.
          </p>
          <p className="score-explainer-note">The two scores are separate: your goals never change the nutrition grade.</p>
        </div>
      </Collapse>
    </div>
  );
}
