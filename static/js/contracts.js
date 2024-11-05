const baseUrl = "https://antoncopiloto.pythonanywhere.com";

function leaded_contractsjs() {
    console.log('leaded contractsjs :)')
}
leaded_contractsjs()
// Function to get CSRF token
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
    var avtiveItem = null
    
    function buildList() {
        var wrapper = document.getElementById('list-wrapper-contracts');
        var url = '${baseUrl}/api/contract-project/';
    
        fetch(url)
        .then((resp) => resp.json())
        .then(function(data) {
            console.log('Data:', data);
            var list = data;
            
            // Clear the existing content
            wrapper.innerHTML = '';
    
            for (var i in list) {
                // Format the created_at date as DD/MM/YYYY
                var createdDate = new Date(list[i].created_at).toLocaleDateString('es-MX', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric'
                });
                var item = `
                    <tr>
                       <td>
                            <i style="color: gray;" class="align-middle me-2 far fa-fw fa-file-word"></i>
                            <a href="/contract/${list[i].id}/">${list[i].name ? list[i].name : 'Unnamed Contract Project'}</a>
                            <button class="btn btn-sm btn-outline-info edit"><i style="color: gray;" class="align-middle me-2 far fa-fw fa-edit"></i></button>
                            <button class="btn btn-sm btn-outline-danger delete"><i style="color: gray;" class="align-middle me-2 far fa-fw fa-trash-alt"></i></button>
                        </td>
                        <td style="text-align: right;">${createdDate}</td>
                    </tr>
                `;
                wrapper.innerHTML += item;
            }
            for (var i in list) {
                var editBtn = document.getElementsByClassName('edit')[i];
                var deleteBtn = document.getElementsByClassName('delete')[i];
                
                editBtn.addEventListener('click', (function(item){
                    return function() {
                        editItem(item)
                    }
                })(list[i]))
    
                // Add click event for delete button (use deleteItem function)
                deleteBtn.addEventListener('click', (function(item) {
                    return function() {
                        deleteItem(item);
                    };
                })(list[i]));
    
            }
        })
        .catch(function(error) {
            console.error('Error fetching data:', error);
        });
    }
    buildList();
    
    var form = document.getElementById('add-contract-project')
    form.addEventListener('submit', function(e){
        e.preventDefault();
        console.log('Form Submitted');
        var url = '${baseUrl}/api/contract-create/';
        var method = 'POST';
    
        if (avtiveItem != null) {
            url = `${baseUrl}/api/contract-update/${avtiveItem.id}/`;
            method = 'PUT';
        }
    
        var name = document.getElementById('name').value;
        fetch(url, {
            method: method, // Use 'POST' or 'PUT' based on the action
            headers: {
                'Content-type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
            body: JSON.stringify({'name': name})
        })
        .then(function(response) {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(function(data) {
            console.log('Success:', data);
            buildList();
            form.reset(); 
            avtiveItem = null; 
            var exampleModal = bootstrap.Modal.getInstance(document.getElementById('exampleModal'));
            exampleModal.hide(); 
        })
        .catch(function(error) {
            console.error('Error:', error);
        });
    
    });
    
    function editItem(item) {
        console.log('Item edit clicked:', item);
        avtiveItem = item;
        document.getElementById('name').value = avtiveItem.name;
    
        // Show the edit modal
        var exampleModal = new bootstrap.Modal(document.getElementById('exampleModal'));
        exampleModal.show();
    }
    
    function deleteItem(item) {
        if (!confirm('¿Está seguro de que desea eliminar este documento?')) {
            return; 
        }
    
        console.log('Delete clicked:', item);
        var url = `${baseUrl}/api/contract-delete/${item.id}/`;
    
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
            buildList(); 
        })
        .catch(function(error) {
            console.error('Error deleting item:', error);
            alert('No se pudo eliminar el documento. Inténtalo nuevamente.');
        });
    }
    