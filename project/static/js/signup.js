document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('signupForm');
  const roleSel = document.getElementById('role');
  const submitBtn = document.getElementById('signupSubmit');
  const commonFields = document.getElementById('commonFields');

  const studentFS = document.getElementById('studentFields');
  const facultyFS = document.getElementById('facultyFields');

  const nshe = document.getElementById('nshe');
  const studentEmail = document.getElementById('studentEmail');
  const studentHint = document.getElementById('studentEmailHint');
  const studentErr = document.getElementById('studentEmailError');

  const facultyEmail = document.getElementById('facultyEmail');
  const facultyHint = document.getElementById('facultyEmailHint');
  const facultyErr = document.getElementById('facultyEmailError');
  const employeeId = document.getElementById('employee_id');
  const department = document.getElementById('department_id');
  const firstName = document.getElementById('first_name');
  const lastName = document.getElementById('last_name');

  const RE = {
    nshe: /^\d{10}$/,
    studentEmail: /^\d{10}@student\.csn\.edu$/,
    facultyEmail: /^[A-Za-z]+(?:\.[A-Za-z]+)*@csn\.edu$/,
    employeeId: /^\d{6,10}$/
  };

  function toggleFields(role) {
    commonFields.classList.toggle('hidden', !role);
    studentFS.classList.toggle('hidden', role !== 'student');
    facultyFS.classList.toggle('hidden', role !== 'faculty');

    studentFS.disabled = role !== 'student';
    facultyFS.disabled = role !== 'faculty';

    submitBtn.disabled = true;
  }

  function syncStudentEmail() {
    const v = nshe.value.trim();
    if (RE.nshe.test(v)) {
      const email = `${v}@student.csn.edu`;
      studentEmail.value = email;
      studentHint.textContent = `Looks good: ${email}`;
      studentHint.classList.add('valid');
      studentHint.classList.remove('invalid');
    } else {
      studentEmail.value = '';
      studentHint.textContent = 'Invalid NSHE format.';
      studentHint.classList.add('invalid');
      studentHint.classList.remove('valid');
    }
  }

  function syncFacultyEmail() {
    const f = firstName.value.trim().toLowerCase();
    const l = lastName.value.trim().toLowerCase();
    if (f && l) {
      const email = `${f}.${l}@csn.edu`;
      facultyEmail.value = email;
      facultyHint.textContent = `Looks good: ${email}`;
      facultyHint.classList.add('valid');
      facultyHint.classList.remove('invalid');
    } else {
      facultyEmail.value = '';
      facultyHint.textContent = 'Enter first and last name to generate email.';
      facultyHint.classList.add('invalid');
      facultyHint.classList.remove('valid');
    }
  }

  function validate() {
    let ok = false;
    if (roleSel.value === 'student') {
      ok = RE.nshe.test(nshe.value) && RE.studentEmail.test(studentEmail.value);
    } else if (roleSel.value === 'faculty') {
      ok = RE.employeeId.test(employeeId.value) && RE.facultyEmail.test(facultyEmail.value) && department.value;
    }
    submitBtn.disabled = !ok;
  }

  // Event bindings
  roleSel.addEventListener('change', e => toggleFields(e.target.value));
  nshe?.addEventListener('input', () => { syncStudentEmail(); validate(); });
  employeeId?.addEventListener('input', validate);
  department?.addEventListener('change', validate);
  firstName?.addEventListener('input', () => { syncFacultyEmail(); validate(); });
  lastName?.addEventListener('input', () => { syncFacultyEmail(); validate(); });

  form.addEventListener('input', validate);
  form.addEventListener('submit', e => {
    if (submitBtn.disabled) e.preventDefault();
  });
});
