const baseUrl = "http://127.0.0.1:7000";
// http://127.0.0.1:7000
// https://antoncopiloto.pythonanywhere.com
// Function to get CSRF token for AJAX requests
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');
var activeItem = null;

function buildChatList() {
    var wrapper = document.getElementById('list-wrapper-chat');
    var url = `${baseUrl}/api/chatsessions/user/`;

    fetch(url)
    .then((resp) => resp.json())
    .then(function(data) {
        console.log('Data:', data);
        var list = data;
        
        // Clear the existing content
        wrapper.innerHTML = '';

        for (var i in list) {
          var createdDate = new Date(list[i].created_at).toLocaleDateString('es-MX', {
              day: '2-digit',
              month: '2-digit',
              year: 'numeric'
          });
          var item = `
              <tr>
                  <td>
                      <i style="color: gray;" class="align-middle me-2 fas fa-fw fa-comments"></i>
                      <a href="/chat/${list[i].id}/">${list[i].name ? list[i].name : 'Unnamed Chat Session'}</a>
                      <button class="btn btn-sm btn-outline-info edit"><i style="color: gray;" class="align-middle me-2 fas fa-fw fa-edit"></i></button>
                      <button class="btn btn-sm btn-outline-danger delete"><i style="color: gray;" class="align-middle me-2 far fa-fw fa-trash-alt"></i></button>
                  </td>
                  <td style="text-align: right;">${createdDate}</td>
              </tr>
          `;
          wrapper.innerHTML += item;
      }

        // Attach edit and delete event listeners to each button
        for (var i in list) {
            var editBtn = document.getElementsByClassName('edit')[i];
            var deleteBtn = document.getElementsByClassName('delete')[i];

            editBtn.addEventListener('click', (function(item){
                return function() {
                    editChatItem(item);
                }
            })(list[i]));

            deleteBtn.addEventListener('click', (function(item) {
                return function() {
                    deleteChatItem(item);
                };
            })(list[i]));
        }
    })
    .catch(function(error) {
        console.error('Error fetching data:', error);
    });
}
buildChatList();

function editChatItem(item) {
    activeItem = item;
    document.getElementById('chat-name').value = activeItem.name;

    var chatModal = new bootstrap.Modal(document.getElementById('chatModal'));
    chatModal.show();
}

function deleteChatItem(item) {
    if (!confirm('¿Estás seguro de que deseas eliminar esta sesión de chat?')) {
        return;
    }

    var url = `${baseUrl}/api/chatsessions/${item.id}/delete/`;

    fetch(url, {
        method: 'DELETE',
        headers: {
            'Content-type': 'application/json',
            'X-CSRFToken': csrftoken,
        }
    })
    .then((response) => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        buildChatList();
    })
    .catch(function(error) {
        console.error('Error deleting item:', error);
        alert('No se puede eliminar la sesión de chat. Inténtalo de nuevo.');
    });
}