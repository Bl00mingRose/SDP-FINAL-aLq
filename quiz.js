document.addEventListener('DOMContentLoaded', () => {
    const cards    = Array.from(document.querySelectorAll('.question-card'));
    const progress = document.getElementById('quiz-progress');
    const modal    = document.getElementById('feedback-modal');
    const fText    = document.getElementById('feedback-text');
    const fExp     = document.getElementById('feedback-explanation');
    const contBtn  = document.getElementById('continue-btn');
    let idx = 0, advanceTimer;
  
    function showCard(i) {
      cards.forEach((c,j)=>{
        c.style.display = j===i ? 'block':'none';
        c.classList.toggle('fade-in', j===i);
      });
      progress.style.width = `${((i+1)/cards.length)*100}%`;
    }
  
    function showFeedback(isCorrect, explanation) {
      fText.textContent = isCorrect ? '✅ Correct!' : '❌ Incorrect';
      fText.style.color = isCorrect
        ? 'var(--correct-color)'
        : 'var(--incorrect-color)';
      fExp.textContent = explanation;
      modal.style.display = 'flex';
  
      // schedule auto-advance
      advanceTimer = setTimeout(() => {
        modal.style.display = 'none';
        advance();
      }, 2000);
  
      // if user clicks Continue, cancel the timer and advance immediately
      contBtn.onclick = () => {
        clearTimeout(advanceTimer);
        modal.style.display = 'none';
        advance();
      };
    }
  
    function advance() {
      idx = Math.min(idx+1, cards.length-1);
      showCard(idx);
    }
  
    document.querySelectorAll('.next-btn').forEach(btn=>{
      btn.addEventListener('click', () => {
        const card = cards[idx];
        const sel  = card.querySelector('input[type="radio"]:checked');
        if (!sel) return alert('Please select an option.');
  
        const isCorrect   = sel.value === card.dataset.correct;
        const explanation = card.dataset.explanation;
        showFeedback(isCorrect, explanation);
      });
    });
  
    document.querySelectorAll('.prev-btn').forEach(btn=>{
      btn.addEventListener('click', () => {
        idx = Math.max(idx-1, 0);
        showCard(idx);
      });
    });
  
    // initial setup
    showCard(0);
  });
  