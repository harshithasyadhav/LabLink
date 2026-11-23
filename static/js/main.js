// LabLink UI Interactions, Dynamic Slot Checking & Equipment Visuals

// High-definition laboratory equipment imagery mapping
const EQUIPMENT_IMAGES = {
  'GPU-CS-4090A': 'https://images.unsplash.com/photo-1591488320449-011701bb6704?auto=format&fit=crop&w=700&q=80',
  'GPU-AI-A6000': 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=700&q=80',
  '3DP-MECH-X1C': 'https://images.unsplash.com/photo-1631541909061-71e349d1f203?auto=format&fit=crop&w=700&q=80',
  'OSC-ECE-1004': 'https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=700&q=80',
  'FPGA-ECE-ZYNQ': 'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=700&q=80',
  'ROB-ROB-TB4': 'https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=700&q=80',
  'DEV-CS-RPI5': 'https://images.unsplash.com/photo-1629654297299-c8506221ca97?auto=format&fit=crop&w=700&q=80',
  'IOT-ECE-LORA': 'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=700&q=80',
  'DEV-ROB-GIGA': 'https://images.unsplash.com/photo-1553406830-ef2513450d76?auto=format&fit=crop&w=700&q=80',
  'OSC-PHYS-500': 'https://images.unsplash.com/photo-1507668077129-56e32842fceb?auto=format&fit=crop&w=700&q=80'
};

document.addEventListener('DOMContentLoaded', () => {
  initModals();
  initSlotBooker();
  initEquipmentDetailViewer();
  initProjectPriorityLivePreview();
  applyEquipmentImages();
});

// Set curated equipment images
function applyEquipmentImages() {
  const images = document.querySelectorAll('[data-eq-code]');
  images.forEach(img => {
    const code = img.getAttribute('data-eq-code');
    if (EQUIPMENT_IMAGES[code]) {
      img.src = EQUIPMENT_IMAGES[code];
    }
  });
}

// Modal handling
function initModals() {
  const openButtons = document.querySelectorAll('[data-modal-open]');
  openButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const targetId = btn.getAttribute('data-modal-open');
      const modal = document.getElementById(targetId);
      if (modal) {
        modal.classList.add('active');
        
        // Handle slot booking modal pre-fill
        const eqId = btn.getAttribute('data-eq-id');
        const eqName = btn.getAttribute('data-eq-name');
        if (eqId && modal.querySelector('#modal_equipment_id')) {
          modal.querySelector('#modal_equipment_id').value = eqId;
          const nameSpan = modal.querySelector('#modal_eq_name');
          if (nameSpan) nameSpan.textContent = eqName || 'Laboratory Resource';
          
          const dateInput = modal.querySelector('#modal_booking_date');
          if (dateInput) {
            checkSlotAvailability(eqId, dateInput.value, modal);
          }
        }
      }
    });
  });

  const closeButtons = document.querySelectorAll('.close-btn, [data-modal-close]');
  closeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const modal = btn.closest('.modal-overlay');
      if (modal) modal.classList.remove('active');
    });
  });

  window.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
      e.target.classList.remove('active');
    }
  });
}

// Real-time slot checking
function initSlotBooker() {
  const modal = document.getElementById('bookingModal');
  if (!modal) return;

  const dateInput = modal.querySelector('#modal_booking_date');
  const eqIdInput = modal.querySelector('#modal_equipment_id');

  if (dateInput) {
    dateInput.addEventListener('change', () => {
      if (eqIdInput && eqIdInput.value) {
        checkSlotAvailability(eqIdInput.value, dateInput.value, modal);
      }
    });
  }
}

async function checkSlotAvailability(eqId, dateStr, modalElement) {
  const slotContainer = modalElement.querySelector('#slot_container');
  if (!slotContainer) return;

  slotContainer.innerHTML = `
    <div style="font-size:0.85rem; color:#64748b; padding:0.85rem; text-align:center; background:#f8fafc; border-radius:8px; border:1px dashed #cbd5e1;">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation: spin 1s linear infinite; vertical-align: middle; margin-right: 6px;">
        <line x1="12" y1="2" x2="12" y2="6"></line>
        <line x1="12" y1="18" x2="12" y2="22"></line>
        <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
        <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
        <line x1="2" y1="12" x2="6" y2="12"></line>
        <line x1="18" y1="12" x2="22" y2="12"></line>
      </svg>
      Verifying real-time lab schedule...
    </div>
  `;

  try {
    const res = await fetch(`/api/equipment/${eqId}/slots?date=${encodeURIComponent(dateStr)}`);
    const data = await res.json();

    if (!res.ok || data.error) {
      slotContainer.innerHTML = `<div style="color:#ef4444; font-size:0.85rem; padding:0.5rem;">${data.error || 'Unable to check availability.'}</div>`;
      return;
    }

    if (!data.slots || data.slots.length === 0) {
      slotContainer.innerHTML = '<div style="font-size:0.85rem; color:#64748b; padding:0.5rem;">No scheduled slots available for this date.</div>';
      return;
    }

    let html = '<div class="slot-pill-group">';
    data.slots.forEach((s, idx) => {
      const radioId = `slot_${idx}`;
      const isApproved = s.status === 'approved';
      const isPending = s.status === 'pending';

      if (isApproved) {
        html += `
          <div>
            <input type="radio" class="slot-radio" id="${radioId}" disabled>
            <label class="slot-label slot-booked" for="${radioId}" title="Slot confirmed for another student">
              <span>${s.slot}</span>
              <span style="font-size:0.68rem; color:#94a3b8; font-weight:700; margin-top:2px;">[RESERVED]</span>
            </label>
          </div>
        `;
      } else if (isPending) {
        html += `
          <div>
            <input type="radio" name="time_slot" value="${s.slot}" class="slot-radio" id="${radioId}" required>
            <label class="slot-label slot-pending" for="${radioId}" title="Another request exists - AI Fairness scoring will evaluate priority">
              <span>${s.slot}</span>
              <span style="font-size:0.68rem; font-weight:800; color:#b45309; margin-top:2px;">[CONTESTED]</span>
            </label>
          </div>
        `;
      } else {
        html += `
          <div>
            <input type="radio" name="time_slot" value="${s.slot}" class="slot-radio" id="${radioId}" required>
            <label class="slot-label" for="${radioId}">
              <span>${s.slot}</span>
              <span style="font-size:0.68rem; color:#10b981; font-weight:700; margin-top:2px;">[AVAILABLE]</span>
            </label>
          </div>
        `;
      }
    });
    html += '</div>';

    slotContainer.innerHTML = html;
  } catch (err) {
    slotContainer.innerHTML = '<div style="color:#ef4444; font-size:0.85rem; padding:0.5rem;">Error contacting scheduling service.</div>';
  }
}

// Equipment detail modal viewer
function initEquipmentDetailViewer() {
  const detailButtons = document.querySelectorAll('[data-view-detail]');
  const detailModal = document.getElementById('equipmentDetailModal');
  if (!detailModal) return;

  detailButtons.forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const eqId = btn.getAttribute('data-view-detail');
      try {
        const res = await fetch(`/api/equipment/${eqId}`);
        const data = await res.json();
        if (data.equipment) {
          const eq = data.equipment;
          detailModal.querySelector('#detail_name').textContent = eq.name;
          detailModal.querySelector('#detail_code').textContent = eq.code;
          detailModal.querySelector('#detail_dept').textContent = eq.department;
          detailModal.querySelector('#detail_category').textContent = eq.category;
          detailModal.querySelector('#detail_location').textContent = eq.location;
          detailModal.querySelector('#detail_specs').textContent = eq.specs || 'Standard lab specifications apply.';
          detailModal.querySelector('#detail_instructions').textContent = eq.instructions || 'Follow central university laboratory SOP guidelines.';
          
          const statusBadge = detailModal.querySelector('#detail_status');
          statusBadge.textContent = eq.status;
          statusBadge.className = `badge badge-${eq.status}`;

          // Wire the direct book button inside the detail modal
          const directBookBtn = detailModal.querySelector('#detail_book_btn');
          if (directBookBtn) {
            directBookBtn.setAttribute('data-eq-id', eq.id);
            directBookBtn.setAttribute('data-eq-name', eq.name);
          }

          detailModal.classList.add('active');
        }
      } catch (err) {
        console.error('Error fetching equipment detail', err);
      }
    });
  });
}

// Interactive Live Priority Score Preview in Project Request Form
function initProjectPriorityLivePreview() {
  const form = document.getElementById('projectForm');
  if (!form) return;

  const deadlineInput = form.querySelector('#project_deadline');
  const targetDateInput = form.querySelector('#preferred_date');
  const urgencySelect = form.querySelector('#urgency');
  const durationSelect = form.querySelector('#duration_hours');

  const previewScoreElem = document.getElementById('live_priority_score');
  const previewDeadlineElem = document.getElementById('preview_deadline_score');
  const previewCritElem = document.getElementById('preview_crit_score');
  const previewDurElem = document.getElementById('preview_dur_score');

  if (!previewScoreElem) return;

  const updatePreview = () => {
    const deadline = deadlineInput.value;
    const targetDate = targetDateInput.value;
    const urgency = urgencySelect.value;
    const duration = parseFloat(durationSelect.value) || 2;

    let sDeadline = 30;
    if (deadline && targetDate) {
      const d1 = new Date(deadline);
      const d2 = new Date(targetDate);
      const diffDays = Math.ceil((d1 - d2) / (1000 * 60 * 60 * 24));
      if (diffDays <= 0) sDeadline = 100;
      else if (diffDays === 1) sDeadline = 95;
      else if (diffDays <= 3) sDeadline = 85;
      else if (diffDays <= 7) sDeadline = 65;
      else if (diffDays <= 14) sDeadline = 45;
      else sDeadline = 30;
    }

    let sCrit = 50;
    if (urgency === 'critical') sCrit = 100;
    else if (urgency === 'high') sCrit = 75;
    else if (urgency === 'medium') sCrit = 50;
    else if (urgency === 'low') sCrit = 25;

    let sDur = 100;
    if (duration > 2) sDur = Math.max(20, 100 - (duration - 2) * 15);

    const sFairness = 85; // Estimated baseline
    const composite = (0.35 * sDeadline + 0.25 * sCrit + 0.15 * sDur + 0.25 * sFairness).toFixed(1);

    previewScoreElem.textContent = composite;
    if (previewDeadlineElem) previewDeadlineElem.textContent = `${sDeadline}/100`;
    if (previewCritElem) previewCritElem.textContent = `${sCrit}/100`;
    if (previewDurElem) previewDurElem.textContent = `${sDur}/100`;
  };

  [deadlineInput, targetDateInput, urgencySelect, durationSelect].forEach(input => {
    if (input) input.addEventListener('change', updatePreview);
  });

  updatePreview();
}
