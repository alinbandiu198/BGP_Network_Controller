function loading(){
    if(loading==0) {
      spinner.classList.add('active');
    } else if(loading==100){
      clearInterval(id);
      window.open("welcome.html","_self");
      spinner.classList.remove('active');
    } else {
      loading = loading + 1;
      if(loading==90){
        spinner.style.animation ="fadeout 1s ease";
      }
    }
}






/*===== SHOW NAVBAR  =====*/ 
const showNavbar = (toggleId, navId, bodyId, headerId) =>{
    const toggle = document.getElementById(toggleId),
    nav = document.getElementById(navId),
    bodypd = document.getElementById(bodyId),
    headerpd = document.getElementById(headerId)

    // Validate that all variables exist
    if(toggle && nav && bodypd && headerpd){
        toggle.addEventListener('click', ()=>{
            // show navbar
            nav.classList.toggle('show')
            // change icon
            toggle.classList.toggle('bx-x')
            // add padding to body
            bodypd.classList.toggle('body-pd')
            // add padding to header
            headerpd.classList.toggle('body-pd')
        })
    }
}

showNavbar('header-toggle','nav-bar','body-pd','header')

/*===== LINK ACTIVE  =====*/ 
const linkColor = document.querySelectorAll('.nav__link')

function colorLink(){
    if(linkColor){
        linkColor.forEach(l=> l.classList.remove('active'))
        this.classList.add('active')
    }
}
linkColor.forEach(l=> l.addEventListener('click', colorLink))


function show() {
    let hidden = document.getElementById('hidden');
    if (hidden.style.display == "none") {
      hidden.style.display = "block"
    } else {
      hidden.style.display = "none"
    }
  }


