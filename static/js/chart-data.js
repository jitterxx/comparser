var randomScalingFactor = function(){ return Math.round(Math.random()*1000)};
	
	var lineChartData = {
			labels : ["January","February","March","April","May","June","July"],
			datasets : [
				{
					label: "My First dataset",
					fillColor : "rgba(220,220,220,0.2)",
					strokeColor : "rgba(220,220,220,1)",
					pointColor : "rgba(220,220,220,1)",
					pointStrokeColor : "#fff",
					pointHighlightFill : "#fff",
					pointHighlightStroke : "rgba(220,220,220,1)",
					data : [randomScalingFactor(),randomScalingFactor(),randomScalingFactor(),randomScalingFactor(),randomScalingFactor(),randomScalingFactor(),randomScalingFactor()]
				},
				{
					label: "My Second dataset",
					fillColor : "rgba(48, 164, 255, 0.2)",
					strokeColor : "rgba(48, 164, 255, 1)",
					pointColor : "rgba(48, 164, 255, 1)",
					pointStrokeColor : "#fff",
					pointHighlightFill : "#fff",
					pointHighlightStroke : "rgba(48, 164, 255, 1)",
					data : [randomScalingFactor(),randomScalingFactor(),randomScalingFactor(),randomScalingFactor(),randomScalingFactor(),randomScalingFactor(),randomScalingFactor()]
				}
			]

		}
		
	var barChartData = {
			labels : ["January","February","March","April","May","June","July"],
			datasets : [
				{
					fillColor : "rgba(220,220,220,0.5)",
					strokeColor : "rgba(220,220,220,0.8)",
					highlightFill: "rgba(220,220,220,0.75)",
					highlightStroke: "rgba(220,220,220,1)",
					data : [randomScalingFactor(),randomScalingFactor(),randomScalingFactor(),randomScalingFactor(),randomScalingFactor(),randomScalingFactor(),randomScalingFactor()]
				},
				{
					fillColor : "rgba(48, 164, 255, 0.2)",
					strokeColor : "rgba(48, 164, 255, 0.8)",
					highlightFill : "rgba(48, 164, 255, 0.75)",
					highlightStroke : "rgba(48, 164, 255, 1)",
					data : [randomScalingFactor(),randomScalingFactor(),randomScalingFactor(),randomScalingFactor(),randomScalingFactor(),randomScalingFactor(),randomScalingFactor()]
				}
			]
	
		}

	var pieData = [
				{
					value: 300,
					color:"#30a5ff",
					highlight: "#62b9fb",
					label: "Blue"
				},
				{
					value: 50,
					color: "#ffb53e",
					highlight: "#fac878",
					label: "Orange"
				},
				{
					value: 100,
					color: "#1ebfae",
					highlight: "#3cdfce",
					label: "Teal"
				},
				{
					value: 120,
					color: "#f9243f",
					highlight: "#f6495f",
					label: "Red"
				}

			];
			
	var doughnutData = [
					{
						value: 300,
						color:"#30a5ff",
						highlight: "#62b9fb",
						label: "Blue"
					},
					{
						value: 50,
						color: "#ffb53e",
						highlight: "#fac878",
						label: "Orange"
					},
					{
						value: 100,
						color: "#1ebfae",
						highlight: "#3cdfce",
						label: "Teal"
					},
					{
						value: 120,
						color: "#f9243f",
						highlight: "#f6495f",
						label: "Red"
					}

				];

function Load_charts(){
	//var chart1 = document.getElementById("line-chart").getContext("2d");
	//window.myLine = new Chart(chart1).Line(lineChartData, {
	//	responsive: true
	//});
	//var chart2 = document.getElementById("bar-chart").getContext("2d");
	//window.myBar = new Chart(chart2).Bar(barChartData, {
	//	responsive : true
	//});
	//var chart3 = document.getElementById("doughnut-chart").getContext("2d");
	//window.myDoughnut = new Chart(chart3).Doughnut(doughnutData, {responsive : true
	//});
	//var chart4 = document.getElementById("pie-chart1").getContext("2d");
	//console.log(pieData);
	//pieData = GetChartData("problem_by_cause");
	//console.log(pieData);
	//window.myPie = new Chart(chart4).Pie(pieData, {responsive : true
	//});

    var start_date = document.getElementById("start_date").value;
    var end_date = document.getElementById("end_date").value;

    GetChartData("problem_by_cause", start_date, end_date);
    GetChartData("problem_by_employee", start_date, end_date);
    GetChartData("problem_by_client", start_date, end_date);
    GetChartData("violation_stats", start_date, end_date);

};

function GetChartData(chart_id, start_date, end_date) {
    jQuery.ajax({
        url: '/control_center/statistics/get_chart_data',
        dataType: 'json',
        data: {chart_id:chart_id, start_date:start_date, end_date:end_date},
        success: function (data) {
                    console.log(chart_id)
                    console.log("Chart data :", data);
                    if (chart_id == "violation_stats"){
                        DrawLineChart(chart_id, data);
                    }
                    else {
                        DrawPieChart(chart_id, data);
                    }

            }
    });
};


function DrawPieChart(chart_id, pieData){

    Chart.defaults.global.defaultFontSize = 6;

	var chart = document.getElementById(chart_id).getContext("2d");
	window.myPie = new Chart(chart).Pie(pieData, {
	    responsive : true,
	    defaultFontSize : 6
	    }
	);
	//console.log(window.myPie.options.legendTemplate);

	document.getElementById("legend_" + chart_id).innerHTML = GenerateLegend(pieData);
}

function DrawLineChart(chart_id, lineChartData){

	var chart = document.getElementById(chart_id).getContext("2d");
	window.myLine = new Chart(chart).Line(lineChartData, {
	    responsive: true
	});
    //document.getElementById("legend_" + chart_id).innerHTML = window.myPie.generateLegend();
}

function GenerateLegend (data) {
    var text = "<div>";

    for (var i=0; i<data.length; i++) {
        text = text + '<div>' + data[i].label + ' - ' + '<span style="color:' + data[i].color + ';">'
                    + data[i].value
                    + '</span></div>';
    }

    text = text + "</div>"
    return text;
}

window.onload = Load_charts();

//Poll our backend for notifications, set some reasonable timeout for your application
var chart_interval = setInterval(function() {
    console.log('Chart data poll...');
    Load_charts();

}, 60000);    //poll every 60 secs.