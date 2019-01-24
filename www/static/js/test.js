/**
 * Created by 10476 on 2019/1/23.
 */

new Vue({
    el: '#example-3',
    data: {
        checkedNames: []
    }
});

var app2 = new Vue({
    el: '#app-2',
    data: {
        message: '页面加载于 ' + new Date().toLocaleString()
    }
});

var app = new Vue({
    el: '#app',
    data: {
        seen: true,
        message: 'Hello Vue!'
    }
});

var app4 = new Vue({
    el: '#app-4',
    data: {
        todos: [
            {text: 'study js'},
            {text: 'study vue'},
            {text: 'all projects'}
        ]
    }
});
app.seen = false;
app4.todos.push({ text: '新项目' })

var app5 = new Vue({
    el:'#app-5',
    data:{
        message:'hello fangfang'
    },
    methods:{
        reverseMessage:function () {
            this.message = this.message.split('').reverse().join('')
        }
    }

});
var app6 = new Vue({
    el:'#app-6',
    data:{
        message:''
    },
    methods:{
        say:function (message) {
            alert(message)
        }
    }
});
        var tag = new Vue({
            el: '#tags',
            data: {
                tags: [{name:'标签一'},{name:'标签二'},{name:'标签三'} ]
            }
        });

        function myClick(){
            tag.tags.pop();
        }

