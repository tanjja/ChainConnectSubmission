var updateBtns = document.getElementsByClassName('update-cart')

for (i = 0; i < updateBtns.length; i++) {
	updateBtns[i].addEventListener('click', function(){
		var productId = this.dataset.product
		var action = this.dataset.action

        // Testing
        // var quantityInput = this.parentNode.querySelector('input[type=number]');
        // var quantity = quantityInput ? quantityInput.value : null; // Use null if quantity is not available

		console.log('productId:', productId, 'action:', action)

        console.log('USER:', user)
        if (user == 'AnonymousUser'){
	        addCookieItem(productId, action)
        }else{
	        updateUserOrder(productId, action) // Test
        }


	})
}


var quantityInputs = document.querySelectorAll('input[name="quantity"]');

quantityInputs.forEach(input => {
    input.addEventListener('change', function() {
        var productId = this.parentNode.querySelector('.update-cart').dataset.product;
        var quantity = this.value;
        console.log('Product ID:', productId, 'New Quantity:', quantity);

        if (user === 'AnonymousUser') {
			console.log('User is not authenticated');
			cart[productId]['quantity'] = Number(quantity);
			console.log('CART:', cart)
			document.cookie ='cart=' + JSON.stringify(cart) + ";domain=;path=/"
        } else {
            console.log('User is authenticated, updating quantity...');
            updateUserOrder(productId, 'update', quantity); // Pass quantity here
        }
    });
});


function updateUserOrder(productId, action, quantity = null){
	console.log('1 User is authenticated, sending data...')

		var url = '/update_item/'
		fetch(url, {
			method:'POST',
			headers:{
				'Content-Type':'application/json',
                'X-CSRFToken': csrftoken,
			}, 
			body:JSON.stringify({
                'productId':productId, 
                'action':action,
                'quantity': quantity //Test
            })
		})
		.then((response) => {
		   return response.json();
		})
		.then((data) => {
		    console.log('data', data)
		});
}

function addCookieItem(productId, action){
	console.log('User is not authenticated')

	
	if (action == 'add'){
		if (cart[productId] == undefined){
		cart[productId] = {'quantity':1}

		} else {
			console.log("adding 1")
			cart[productId]['quantity'] += 1
		}
	}

	if (action == 'remove'){
		cart[productId]['quantity'] -= 1

		if (cart[productId]['quantity'] <= 0){
			console.log('Remove Item')
			delete cart[productId];
		}
	}
	console.log('CART:', cart)
	document.cookie ='cart=' + JSON.stringify(cart) + ";domain=;path=/"
	// location.reload()
}