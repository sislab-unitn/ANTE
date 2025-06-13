const get_prolific_id = () => {
  fetch('prolific_id', {
    method: 'get',
  })
    .then(Result => Result.json())
    .then(data => {
      console.log(data);
      // your code comes here
      let text = data.prolific_id;
      if (data.prolific_id == null) {
          // Move to a new location or you can do something else
          window.location.href = "sign_in";
        
      }
      document.getElementById('prolific_id').innerHTML = text;

    })
    .catch(errorMsg => {
      console.log(errorMsg);
    });
};
const get_completion_code = () => {
  fetch('completion/get_completion_code', {
    method: 'get',
  })
    .then(Result => Result.json())
    .then(data => {
      if (data.done == true) {
        document.getElementById('completion_code').innerHTML = data.completion_code;

      } else {
        document.getElementById('completion_code').innerHTML = 'Completa il task prima. Verrai reindirizzato alla pagina del task in 3 secondi.';
        window.setTimeout(function () {
          // Move to a new location or you can do something else
          window.location.href = "data_collection";
        }, 3000);
      }
    })
    .catch(errorMsg => {
      console.log(errorMsg);
    });

};
const go_to_data_collection = () => {
  window.location.href = "data_collection";
};
showExample = (form) => {
  // search by name inside the form
  console.log(form);
  let id = form.id;
  send_example(form);
  let correct_child = document.getElementById(id).querySelectorAll('.correct');
  correct_child.forEach((element) => { element.classList.add('is-valid');});
  // document.getElementById(id).querySelectorAll('.correct')[0].classList.add('is-valid');
  let child = document.getElementById(id).querySelectorAll('.incorrect');
  child.forEach((element) => { element.classList.add('is-invalid');});
  let children = document.getElementById(id).querySelectorAll('.form-check-input');
  children.forEach((element) => {element.setAttribute('disabled','')});
  let answer = document.getElementById(id).querySelector('.answer');
  answer.removeAttribute('hidden');
  let button = document.getElementById(id).querySelector('.btn');
  button.setAttribute('hidden','');
  // check if three answers are hidden
  let answers = document.querySelectorAll('.answer');
  let count = 0;
  answers.forEach((element) => {if (!element.hasAttribute('hidden')) {count += 1;}});
  if(count==4){
    document.getElementById('submit').classList.remove('d-none');
  }
};

send_example = (form) => {
  const formEl = form;
  const payload = new FormData(formEl);
  console.log(payload);
  fetch('example/form', {
    method: 'POST',
    body: payload,
  })

    .then(Result => Result.json())
    .then(data => {
      console.log(data);
    })
    .catch(errorMsg => {
      console.log(errorMsg);
    });
};
const validateForm = () => {
  let input = document.getElementById('elicitation').value;
  let string = input.replace(/\s\s+/g, ' ');
  if (string.length >= 1) {
    document.getElementById('submit').removeAttribute('disabled');
    document.getElementById('elicitation').classList.remove('is-invalid');
    document.getElementById('elicitation').classList.add('is-valid');
  }
  else {
    document.getElementById('submit').setAttribute('disabled', 'disabled');
    document.getElementById('elicitation').classList.remove('is-valid');
    document.getElementById('elicitation').classList.add('is-invalid');
  }
};

const update_narrative = () => {
  fetch('data_collection/get_narrative', {
    method: 'get',
  })
    .then(Result => Result.json())
    .then(data => {
      console.log(data);
      // your code comes here
      let text = data.text;
      if (data.highlight_positive.length > 0) {
        for (let i of data.highlight_positive) { text = text.replace(i, "<mark class=green>" + i + "</mark>") }
      }
      if (data.highlight_negative.length > 0) {
        for (let i of data.highlight_negative) { text = text.replace(i, "<mark class=red>" + i + "</mark>") }
      }
      document.getElementById('narrative').innerHTML = text;
      console.log(data.id);
      document.getElementById('narrative_form').reset();
      document.getElementById('narrative_id').value = data.id;
      if (data.elicitation != null) {
        document.getElementById('elicitation').value = data.elicitation;
        document.getElementById('submit').removeAttribute('disabled');
      }
      else {
        document.getElementById('elicitation').value = '';
        document.getElementById('submit').setAttribute('disabled', 'disabled');
      }
    })
    .catch(errorMsg => {
      console.log(errorMsg);
    });
    // wait 1 second and check if the form is completed
    setTimeout(form_completion, 1000);
};

// const form_completion = () => {
//   // check that the progress is 100%
//   fetch('data_collection/get_counts', {
//     method: 'get',
//   })
//     .then(Result => Result.json())
//     .then(data => {
//       console.log(data);
//         // disable form
//         redirect_completion();
//     })
//     .catch(errorMsg => {
//       console.log(errorMsg);
//     });
// }
// const redirect_completion = () => {
//   fetch('check_cookie', {
//     method: 'post',
//   })
//     .then(Result => Result.json())
//     .then(data => {
//       console.log(data)
//       if (data.expired == true) {
//         window.location.href = "completion";
//       }
//     }
//       )
//     .catch(errorMsg => {
//       console.log(errorMsg);
//     });

// };
const form_completion = () => {
  fetch('check_cookie', {
    method: 'post',
  })
    .then(Result => Result.json())
    .then(data => {
      console.log(data)
      if (data.expired == true) {
        // delay 1 second to make sure the form is submitted
        // setTimeout(function(){ window.location.href = "completion"; }, 1000);
        window.location.href = "completion";
      }
    }
      )
    .catch(errorMsg => {
      console.log(errorMsg);
    });

};
const next_narrative = () => {
  const formEl = document.getElementById('narrative_form');
  const payload = new FormData(formEl);
  fetch('data_collection/get_narrative', {
    method: 'POST',
    body: payload,
  })

    .then(Result => Result.json())
    .then(data => {
      console.log(data);
      // your code comes here
      let text = ''
      if (data.text != null && data.text.length > 0) {
        text = data.text;
      }
      if (data.highlight_positive != null && data.highlight_positive.length > 0) {
        for (let i of data.highlight_positive) { text = text.replace(i, "<mark class=green>" + i + "</mark>") }
      }
      if (data.highlight_negative != null && data.highlight_negative.length > 0) {
        for (let i of data.highlight_negative) { text = text.replace(i, "<mark class=red>" + i + "</mark>") }
      }
      if (data.text != null) {
        document.getElementById('narrative').innerHTML = text;
      }

      if (data.id != null) {
        document.getElementById('narrative_form').reset();
        document.getElementById('narrative_id').value = data.id;
      }
      if (data.elicitation != null) {
        document.getElementById('elicitation').value = data.elicitation;
        document.getElementById('submit').removeAttribute('disabled');
      }
      else {
        document.getElementById('elicitation').value = '';
        document.getElementById('submit').setAttribute('disabled', 'disabled');
      }
      if (data.completed != null && data.completed) {
        document.getElementById('submit').classList.add('d-none');
        document.getElementById('narrative').setAttribute('hidden', 'hidden');
        document.getElementById('narrative_form').setAttribute('hidden', 'hidden');
        document.getElementById('thanks').removeAttribute('hidden');
        let current = parseInt(document.getElementById('current').innerHTML);
        console.log(current);
        let total = parseInt(document.getElementById('total_narratives').innerHTML);
        if (current >= total) {
          document.getElementById('progress_bar').classList.add('bg-success');
        }

      }
      else {
        document.getElementById('submit').classList.remove('d-none');
        document.getElementById('narrative').removeAttribute('hidden');
        document.getElementById('narrative_form').removeAttribute('hidden');
        document.getElementById('thanks').setAttribute('hidden', 'hidden');
      }
      form_completion();
    })
    .catch(errorMsg => {
      console.log(errorMsg);
    });

  document.getElementById('elicitation').classList.remove('is-valid');
  document.getElementById('elicitation').classList.remove('is-invalid');
  next_progress();
};
const update_progress_bar = (current, total) => {
  let progress_bar = document.getElementById('progress_bar');
  progress_bar.setAttribute('style', 'width: ' + (current/ total) * 100 + '%');
  if (current < total) {
    progress_bar.classList.remove('bg-success');
  }
  else{
    progress_bar.classList.add('bg-success');
  }
}

const next_progress = () => {
  document.getElementById('current').innerHTML = Math.min(parseInt(document.getElementById('current').innerHTML) + 1, parseInt(document.getElementById('total_narratives').innerHTML));
  update_progress_bar(document.getElementById('current').innerHTML, document.getElementById('total_narratives').innerHTML);
};

const update_progress = () => {
  fetch('data_collection/get_counts', {
    method: 'get',
  })
    .then(Result => Result.json())
    .then(data => {
      console.log(data);
      document.getElementById('total_narratives').innerHTML = data.total;
      let curr =  0;
      if (data.completed != null && data.completed >= 0) {
        curr = data.completed;
      }
      document.getElementById('current').innerHTML = curr
      update_progress_bar(curr, data.total);
    })
    .catch(errorMsg => {
      console.log(errorMsg);
    });

};
