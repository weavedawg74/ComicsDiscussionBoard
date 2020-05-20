//javascript, jQuery

$(document).ready(function(){
    $("#button").click((e) => {
        e.preventDefault();
        alert('hello');  
    $.ajax({
      url:`https://api.shortboxed.com/comics/v1/new`
    }) 
    .done((res)=>{
      let comics = res.Search;
      $.each(comics, (i, e)=>{
        let title = e.title
        let publisher = e.publisher
        console.log("title", title)
       $("#results").append({title}, {publisher}) 
      })
    })
  })
})
