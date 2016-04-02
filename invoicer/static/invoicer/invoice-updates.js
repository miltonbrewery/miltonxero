/* Expects configuration information in an array called params */

var autocompletes = new Array();

var updateDesc = function(basename, response){
    document.getElementById(basename+"-abv").innerHTML = response['abv'];
    document.getElementById(basename+"-barrels").innerHTML = response['barrels'];
    document.getElementById(basename+"-barrelprice").innerHTML = response['barrelprice'];
    document.getElementById(basename+"-total").innerHTML = response['total'];
    document.getElementById(basename+"-incvat").innerHTML = response['incvat'];
    document.getElementById(basename+"-account").innerHTML = response['account'];
    document.getElementById(basename+"-error").innerHTML = response['error'];
};

var addAutoComplete = function(basename){
    autocompletes[basename] = new autoComplete({
	selector: 'input[name="'+basename+'"]',
	minChars: 5,
	cache: false,
	source: function(term, response){
            $.getJSON(params['item_completions_url'], { q: term },
		      function(data) { response(data); });
	},
	onSelect: function(event, term, item){
            $.getJSON(params['item_details_url'],
		      { q: term, b: params['priceband'] },
		      function(data) {
			  updateDesc(basename, data);
			  updateTotals();
		      });
	},
    });
};

var updateTotals = function() {
    var total = 0.0;
    $("td.exvat").each(function(i, e) {
	s = e.textContent;
	if (s == "") {
	    s = "0.00";
	};
	total = total + parseFloat(s);
    });
    document.getElementById("total-ex-vat").innerHTML = total.toFixed(2);
    var total = 0.0;
    $("td.incvat").each(function(i, e) {
	s = e.textContent;
	if (s == "") {
	    s = "0.00";
	};
	total = total + parseFloat(s);
    });
    document.getElementById("total-inc-vat").innerHTML = total.toFixed(2);
};
